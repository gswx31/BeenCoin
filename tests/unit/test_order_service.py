import pytest
from decimal import Decimal
from app.models.database import SpotAccount
from app.schemas.order import OrderCreate, OrderSide
from app.services import order_service

@pytest.mark.asyncio
async def test_create_order_buy_market(session, mocker):
    # Binance API 호출 모킹
    mocker.patch("app.services.order_service.get_current_price", return_value=Decimal("100"))
    mocker.patch("app.services.order_service.execute_market_order", return_value=Decimal("100"))

    # 계정 생성
    account = SpotAccount(user_id=1, usdt_balance=Decimal("10000"))
    session.add(account)
    session.commit()

    # 주문 생성
    order_data = OrderCreate(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type="MARKET",
        quantity=Decimal("0.1")
    )

    order = await order_service.create_order(session, user_id=1, order_data=order_data)

    assert order.id is not None
    assert order.status == "FILLED"
    assert order.symbol == "BTCUSDT"
