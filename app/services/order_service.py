# app/services/order_service.py
from sqlmodel import Session, select
from app.models.database import (
    Order, SpotPosition, FuturesPosition, 
    SpotAccount, FuturesAccount, Transaction,
    TradingType, OrderSide, OrderType, OrderStatus,
    PositionSide, MarginType, User
)
from app.services.binance_service import binance_service
from decimal import Decimal
from typing import Optional, List, Dict
from datetime import datetime
from fastapi import HTTPException
import asyncio

class OrderService:
    """통합 주문 서비스"""
    
    def __init__(self):
        self.fee_rate = Decimal('0.001')  # 0.1% 수수료
        
    async def create_order(
        self, 
        session: Session, 
        user_id: int, 
        order_data: Dict
    ) -> Order:
        """주문 생성 (현물/선물)"""
        
        # 주문 타입 확인
        trading_type = order_data.get('trading_type', TradingType.SPOT)
        
        if trading_type == TradingType.SPOT:
            return await self._create_spot_order(session, user_id, order_data)
        else:
            return await self._create_futures_order(session, user_id, order_data)
    
    async def _create_spot_order(
        self, 
        session: Session, 
        user_id: int, 
        order_data: Dict
    ) -> Order:
        """현물 주문 처리"""
        
        # 계정 확인
        account = session.exec(
            select(SpotAccount).where(SpotAccount.user_id == user_id)
        ).first()
        
        if not account:
            # 계정 생성
            account = SpotAccount(
                user_id=user_id,
                usdt_balance=Decimal('1000000.00')
            )
            session.add(account)
            session.commit()
            session.refresh(account)
        
        # 현재 가격 조회
        symbol = order_data['symbol']
        current_price = await binance_service.get_current_price(symbol)
        
        # 주문 생성
        order = Order(
            user_id=user_id,
            trading_type=TradingType.SPOT,
            symbol=symbol,
            side=OrderSide(order_data['side']),
            order_type=OrderType(order_data['order_type']),
            quantity=Decimal(str(order_data['quantity'])),
            price=Decimal(str(order_data.get('price', current_price))),
            status=OrderStatus.PENDING
        )
        
        session.add(order)
        session.commit()
        session.refresh(order)
        
        # 주문 실행
        if order.order_type == OrderType.MARKET:
            await self._execute_spot_market_order(session, account, order, current_price)
        else:  # LIMIT
            # 실제로는 WebSocket으로 모니터링해야 하지만, 여기서는 단순화
            asyncio.create_task(
                self._monitor_spot_limit_order(session, account, order)
            )
        
        return order
    
    async def _create_futures_order(
        self, 
        session: Session, 
        user_id: int, 
        order_data: Dict
    ) -> Order:
        """선물 주문 처리"""
        
        # 계정 확인
        account = session.exec(
            select(FuturesAccount).where(FuturesAccount.user_id == user_id)
        ).first()
        
        if not account:
            # 계정 생성
            account = FuturesAccount(
                user_id=user_id,
                usdt_balance=Decimal('1000000.00'),
                available_balance=Decimal('1000000.00')
            )
            session.add(account)
            session.commit()
            session.refresh(account)
        
        # 현재 가격 조회
        symbol = order_data['symbol']
        current_price = await binance_service.get_current_price(symbol, futures=True)
        
        # 레버리지 확인
        leverage = order_data.get('leverage', 1)
        if leverage < 1 or leverage > 125:
            raise HTTPException(status_code=400, detail="Invalid leverage (1-125)")
        
        # 주문 생성
        order = Order(
            user_id=user_id,
            trading_type=TradingType.FUTURES,
            symbol=symbol,
            side=OrderSide(order_data['side']),
            order_type=OrderType(order_data['order_type']),
            quantity=Decimal(str(order_data['quantity'])),
            price=Decimal(str(order_data.get('price', current_price))),
            leverage=leverage,
            position_side=PositionSide(order_data.get('position_side', 'BOTH')),
            status=OrderStatus.PENDING
        )
        
        session.add(order)
        session.commit()
        session.refresh(order)
        
        # 주문 실행
        if order.order_type == OrderType.MARKET:
            await self._execute_futures_market_order(session, account, order, current_price)
        else:
            asyncio.create_task(
                self._monitor_futures_limit_order(session, account, order)
            )
        
        return order
    
    async def _execute_spot_market_order(
        self,
        session: Session,
        account: SpotAccount,
        order: Order,
        price: Decimal
    ):
        """현물 시장가 주문 실행"""
        
        quantity = order.quantity
        total_cost = quantity * price
        fee = total_cost * self.fee_rate
        
        if order.side == OrderSide.BUY:
            # 매수: USDT로 코인 구매
            required_amount = total_cost + fee
            
            if account.usdt_balance < required_amount:
                order.status = OrderStatus.REJECTED
                session.add(order)
                session.commit()
                raise HTTPException(status_code=400, detail="Insufficient balance")
            
            # 잔고 차감
            account.usdt_balance -= required_amount
            
            # 포지션 업데이트
            position = session.exec(
                select(SpotPosition).where(
                    SpotPosition.account_id == account.id,
                    SpotPosition.symbol == order.symbol
                )
            ).first()
            
            if not position:
                position = SpotPosition(
                    account_id=account.id,
                    symbol=order.symbol,
                    quantity=Decimal('0'),
                    average_price=Decimal('0')
                )
                session.add(position)
            
            # 평균 단가 계산
            total_value = position.quantity * position.average_price
            new_total_value = total_value + total_cost
            new_quantity = position.quantity + quantity
            
            position.quantity = new_quantity
            position.average_price = new_total_value / new_quantity if new_quantity > 0 else Decimal('0')
            position.current_price = price
            position.current_value = position.quantity * price
            position.unrealized_profit = (price - position.average_price) * position.quantity
            
        else:  # SELL
            # 매도: 코인을 USDT로 판매
            position = session.exec(
                select(SpotPosition).where(
                    SpotPosition.account_id == account.id,
                    SpotPosition.symbol == order.symbol
                )
            ).first()
            
            if not position or position.quantity < quantity:
                order.status = OrderStatus.REJECTED
                session.add(order)
                session.commit()
                raise HTTPException(status_code=400, detail="Insufficient coin balance")
            
            # 수익 계산
            profit = (price - position.average_price) * quantity - fee
            
            # 포지션 감소
            position.quantity -= quantity
            if position.quantity == 0:
                session.delete(position)
            else:
                position.current_value = position.quantity * price
                position.unrealized_profit = (price - position.average_price) * position.quantity
            
            # 잔고 증가
            account.usdt_balance += (total_cost - fee)
            account.total_profit += profit
        
        # 주문 상태 업데이트
        order.status = OrderStatus.FILLED
        order.filled_quantity = quantity
        order.average_price = price
        order.updated_at = datetime.utcnow()
        
        # 거래 기록
        transaction = Transaction(
            user_id=order.user_id,
            order_id=order.id,
            trading_type=TradingType.SPOT,
            symbol=order.symbol,
            side=order.side,
            quantity=quantity,
            price=price,
            fee=fee
        )
        
        session.add(account)
        session.add(order)
        session.add(transaction)
        session.commit()
    
    async def _execute_futures_market_order(
        self,
        session: Session,
        account: FuturesAccount,
        order: Order,
        price: Decimal
    ):
        """선물 시장가 주문 실행"""
        
        quantity = order.quantity
        leverage = order.leverage or 1
        notional = quantity * price
        required_margin = notional / Decimal(leverage)
        fee = notional * self.fee_rate
        
        # 마진 확인
        if account.available_balance < (required_margin + fee):
            order.status = OrderStatus.REJECTED
            session.add(order)
            session.commit()
            raise HTTPException(status_code=400, detail="Insufficient margin")
        
        # 기존 포지션 확인
        position = session.exec(
            select(FuturesPosition).where(
                FuturesPosition.user_id == order.user_id,
                FuturesPosition.symbol == order.symbol,
                FuturesPosition.is_active == True
            )
        ).first()
        
        if order.side == OrderSide.BUY:
            # 롱 포지션 오픈/추가
            if position and position.position_side == PositionSide.SHORT:
                # 반대 포지션이 있으면 먼저 청산
                await self._close_futures_position(session, account, position, price)
                position = None
            
            if not position:
                # 새 포지션 생성
                liquidation_price = await binance_service.calculate_liquidation_price(
                    price, quantity, leverage, "LONG", 
                    order_data.get('margin_type', 'ISOLATED')
                )
                
                position = FuturesPosition(
                    user_id=order.user_id,
                    symbol=order.symbol,
                    position_side=PositionSide.LONG,
                    quantity=quantity,
                    entry_price=price,
                    mark_price=price,
                    liquidation_price=liquidation_price,
                    leverage=leverage,
                    margin_type=MarginType(order_data.get('margin_type', 'ISOLATED')),
                    margin=required_margin
                )
                session.add(position)
            else:
                # 기존 포지션에 추가
                total_value = position.quantity * position.entry_price + notional
                new_quantity = position.quantity + quantity
                position.quantity = new_quantity
                position.entry_price = total_value / new_quantity
                position.margin += required_margin
        
        else:  # SELL - 숏 포지션
            if position and position.position_side == PositionSide.LONG:
                await self._close_futures_position(session, account, position, price)
                position = None
            
            if not position:
                liquidation_price = await binance_service.calculate_liquidation_price(
                    price, quantity, leverage, "SHORT",
                    order_data.get('margin_type', 'ISOLATED')
                )
                
                position = FuturesPosition(
                    user_id=order.user_id,
                    symbol=order.symbol,
                    position_side=PositionSide.SHORT,
                    quantity=quantity,
                    entry_price=price,
                    mark_price=price,
                    liquidation_price=liquidation_price,
                    leverage=leverage,
                    margin_type=MarginType(order_data.get('margin_type', 'ISOLATED')),
                    margin=required_margin
                )
                session.add(position)
            else:
                total_value = position.quantity * position.entry_price + notional
                new_quantity = position.quantity + quantity
                position.quantity = new_quantity
                position.entry_price = total_value / new_quantity
                position.margin += required_margin
        
        # 계정 업데이트
        account.total_margin += required_margin
        account.available_balance -= (required_margin + fee)
        
        # 주문 완료
        order.status = OrderStatus.FILLED
        order.filled_quantity = quantity
        order.average_price = price
        order.updated_at = datetime.utcnow()
        
        # 거래 기록
        transaction = Transaction(
            user_id=order.user_id,
            order_id=order.id,
            trading_type=TradingType.FUTURES,
            symbol=order.symbol,
            side=order.side,
            quantity=quantity,
            price=price,
            fee=fee
        )
        
        session.add(account)
        session.add(order)
        session.add(transaction)
        session.commit()
    
    async def _close_futures_position(
        self,
        session: Session,
        account: FuturesAccount,
        position: FuturesPosition,
        close_price: Decimal
    ):
        """선물 포지션 청산"""
        
        # PnL 계산
        if position.position_side == PositionSide.LONG:
            pnl = (close_price - position.entry_price) * position.quantity
        else:  # SHORT
            pnl = (position.entry_price - close_price) * position.quantity
        
        # 수수료
        fee = position.quantity * close_price * self.fee_rate
        net_pnl = pnl - fee
        
        # 계정 업데이트
        account.total_realized_pnl += net_pnl
        account.total_margin -= position.margin
        account.available_balance += (position.margin + net_pnl)
        
        # 포지션 비활성화
        position.is_active = False
        position.realized_pnl = net_pnl
        position.updated_at = datetime.utcnow()
        
        session.add(account)
        session.add(position)
    
    async def _monitor_spot_limit_order(
        self,
        session: Session,
        account: SpotAccount,
        order: Order
    ):
        """현물 지정가 주문 모니터링 (단순화된 버전)"""
        # 실제로는 WebSocket으로 실시간 체크해야 함
        await asyncio.sleep(2)  # 2초 후 체결 가정
        
        # 체결 처리
        await self._execute_spot_market_order(
            session, account, order, order.price
        )
    
    async def _monitor_futures_limit_order(
        self,
        session: Session,
        account: FuturesAccount,
        order: Order
    ):
        """선물 지정가 주문 모니터링"""
        await asyncio.sleep(2)
        await self._execute_futures_market_order(
            session, account, order, order.price
        )
    
    def get_user_orders(
        self,
        session: Session,
        user_id: int,
        trading_type: Optional[TradingType] = None,
        limit: int = 50
    ) -> List[Order]:
        """사용자 주문 내역 조회"""
        query = select(Order).where(Order.user_id == user_id)
        
        if trading_type:
            query = query.where(Order.trading_type == trading_type)
        
        query = query.order_by(Order.created_at.desc()).limit(limit)
        
        return session.exec(query).all()
    
    def get_account_summary(
        self,
        session: Session,
        user_id: int,
        trading_type: TradingType = TradingType.SPOT
    ) -> Dict:
        """계정 요약 정보"""
        
        if trading_type == TradingType.SPOT:
            account = session.exec(
                select(SpotAccount).where(SpotAccount.user_id == user_id)
            ).first()
            
            if not account:
                return {
                    "usdt_balance": 0,
                    "total_profit": 0,
                    "positions": []
                }
            
            positions = session.exec(
                select(SpotPosition).where(SpotPosition.account_id == account.id)
            ).all()
            
            return {
                "usdt_balance": float(account.usdt_balance),
                "total_profit": float(account.total_profit),
                "positions": [
                    {
                        "symbol": p.symbol,
                        "quantity": float(p.quantity),
                        "average_price": float(p.average_price),
                        "current_value": float(p.current_value),
                        "unrealized_profit": float(p.unrealized_profit)
                    }
                    for p in positions
                ]
            }
        
        else:  # FUTURES
            account = session.exec(
                select(FuturesAccount).where(FuturesAccount.user_id == user_id)
            ).first()
            
            if not account:
                return {
                    "usdt_balance": 0,
                    "available_balance": 0,
                    "total_margin": 0,
                    "total_unrealized_pnl": 0,
                    "total_realized_pnl": 0,
                    "positions": []
                }
            
            positions = session.exec(
                select(FuturesPosition).where(
                    FuturesPosition.user_id == user_id,
                    FuturesPosition.is_active == True
                )
            ).all()
            
            # 미실현 PnL 계산
            total_unrealized_pnl = Decimal('0')
            for position in positions:
                # 실시간 가격으로 업데이트 (실제 구현시)
                if position.position_side == PositionSide.LONG:
                    position.unrealized_pnl = (position.mark_price - position.entry_price) * position.quantity
                else:
                    position.unrealized_pnl = (position.entry_price - position.mark_price) * position.quantity
                
                total_unrealized_pnl += position.unrealized_pnl
            
            account.total_unrealized_pnl = total_unrealized_pnl
            
            return {
                "usdt_balance": float(account.usdt_balance),
                "available_balance": float(account.available_balance),
                "total_margin": float(account.total_margin),
                "total_unrealized_pnl": float(account.total_unrealized_pnl),
                "total_realized_pnl": float(account.total_realized_pnl),
                "positions": [
                    {
                        "symbol": p.symbol,
                        "side": p.position_side.value,
                        "quantity": float(p.quantity),
                        "entry_price": float(p.entry_price),
                        "mark_price": float(p.mark_price),
                        "liquidation_price": float(p.liquidation_price),
                        "leverage": p.leverage,
                        "margin": float(p.margin),
                        "unrealized_pnl": float(p.unrealized_pnl),
                        "percentage_pnl": float(p.percentage_pnl)
                    }
                    for p in positions
                ]
            }

# 전역 인스턴스
order_service = OrderService()