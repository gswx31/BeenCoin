// client/src/components/trading/FuturesTrading.js
// =============================================================================
// 선물 거래 메인 컴포넌트 - 차트, 주문, 호가창 통합
// =============================================================================
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useMarket } from '../../contexts/MarketContext';
import { useFutures } from '../../contexts/FuturesContext';
import { formatPrice } from '../../utils/formatPrice';
import TradingChart from './TradingChart';
import FuturesOrderForm from './FuturesOrderForm';
import OrderBook from './OrderBook';
import RecentTrades from './RecentTrades';
import PositionsList from './PositionsList';

const FuturesTrading = () => {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { coins, realtimePrices, isConnected, loading: marketLoading } = useMarket();
  const { account, positions, fetchPositions } = useFutures();

  const [coin, setCoin] = useState(null);
  const [currentPrice, setCurrentPrice] = useState(0);
  const [priceChange, setPriceChange] = useState(0);

  // 인증 체크
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: `/trade/${symbol}` } });
    }
  }, [isAuthenticated, navigate, symbol]);

  // 코인 정보 로드
  useEffect(() => {
    if (coins.length > 0) {
      const foundCoin = coins.find((c) => c.symbol === symbol);
      if (foundCoin) {
        setCoin(foundCoin);
        setPriceChange(parseFloat(foundCoin.change) || 0);
      } else {
        // 기본 코인 정보 생성
        setCoin({
          symbol,
          name: symbol.replace('USDT', ''),
          icon: '₿',
          color: '#F7931A',
        });
      }
    }
  }, [symbol, coins]);

  // 실시간 가격 업데이트
  useEffect(() => {
    if (realtimePrices[symbol]) {
      const newPrice = realtimePrices[symbol];
      
      // 가격 변화 계산
      if (currentPrice > 0) {
        const change = ((newPrice - currentPrice) / currentPrice) * 100;
        if (Math.abs(change) > 0.01) {
          // 0.01% 이상 변화만 업데이트
        }
      }
      
      setCurrentPrice(newPrice);
    }
  }, [realtimePrices, symbol]);

  // 현재 심볼의 오픈 포지션
  const symbolPositions = positions.filter(
    (pos) => pos.symbol === symbol && pos.status === 'OPEN'
  );

  // 로딩 상태
  if (!isAuthenticated) return null;

  if (marketLoading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-accent"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 상단 헤더 */}
      <TradingHeader
        coin={coin}
        currentPrice={currentPrice}
        priceChange={priceChange}
        isConnected={isConnected}
        account={account}
      />

      {/* 메인 그리드 */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 차트 영역 (3/4) */}
        <div className="lg:col-span-3 space-y-6">
          <TradingChart symbol={symbol} />
          
          {/* 현재 포지션 */}
          {symbolPositions.length > 0 && (
            <CurrentPositions 
              positions={symbolPositions} 
              currentPrice={currentPrice}
            />
          )}
        </div>

        {/* 주문 폼 (1/4) */}
        <div className="lg:col-span-1">
          <FuturesOrderForm symbol={symbol} currentPrice={currentPrice} />
        </div>
      </div>

      {/* 하단 그리드 - 호가창, 체결내역 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <OrderBook symbol={symbol} currentPrice={currentPrice} />
        <RecentTrades symbol={symbol} />
      </div>

      {/* 전체 포지션 목록 */}
      <PositionsList />
    </div>
  );
};

// =============================================================================
// 트레이딩 헤더 컴포넌트
// =============================================================================
const TradingHeader = ({ coin, currentPrice, priceChange, isConnected, account }) => {
  const isPositive = priceChange >= 0;

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* 코인 정보 */}
        <div className="flex items-center space-x-4">
          {coin && (
            <div
              className="w-14 h-14 rounded-full flex items-center justify-center text-2xl font-bold"
              style={{ backgroundColor: coin.color || '#4fd1c5' }}
            >
              {coin.icon || coin.symbol?.charAt(0)}
            </div>
          )}
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-2xl font-bold">{coin?.name || 'Loading...'}</h1>
              <span className="text-gray-400">{coin?.symbol}</span>
              <span className="px-2 py-1 bg-purple-600 rounded text-xs font-semibold">
                선물
              </span>
            </div>
            <div className="flex items-center space-x-2 mt-1">
              {isConnected ? (
                <span className="flex items-center text-green-400 text-sm">
                  <span className="w-2 h-2 bg-green-400 rounded-full mr-1 animate-pulse"></span>
                  실시간
                </span>
              ) : (
                <span className="flex items-center text-yellow-400 text-sm">
                  <span className="w-2 h-2 bg-yellow-400 rounded-full mr-1"></span>
                  연결 중...
                </span>
              )}
            </div>
          </div>
        </div>

        {/* 가격 정보 */}
        <div className="text-right">
          <p className="text-sm text-gray-400 mb-1">현재가</p>
          <p className="text-4xl font-bold text-accent">
            ${currentPrice > 0 ? formatPrice(currentPrice) : '---'}
          </p>
          <p className={`text-sm mt-1 ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
            {isPositive ? '▲' : '▼'} {isPositive ? '+' : ''}
            {priceChange.toFixed(2)}% (24h)
          </p>
        </div>

        {/* 계정 정보 */}
        {account && (
          <div className="bg-gray-700 rounded-lg p-4 min-w-[200px]">
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">사용 가능</span>
                <span className="font-semibold">
                  ${formatPrice(account.available_balance || account.balance)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">사용 중</span>
                <span className="text-yellow-400">
                  ${formatPrice(account.margin_used || 0)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">미실현 손익</span>
                <span
                  className={
                    (account.unrealized_pnl || 0) >= 0
                      ? 'text-green-400'
                      : 'text-red-400'
                  }
                >
                  {(account.unrealized_pnl || 0) >= 0 ? '+' : ''}
                  ${formatPrice(account.unrealized_pnl || 0)}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// =============================================================================
// 현재 포지션 미니 뷰 컴포넌트
// =============================================================================
const CurrentPositions = ({ positions, currentPrice }) => {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-lg font-semibold mb-3">현재 포지션</h3>
      <div className="space-y-2">
        {positions.map((pos) => {
          // 실시간 PnL 계산
          let unrealizedPnl = pos.unrealized_pnl;
          if (currentPrice > 0 && pos.entry_price) {
            if (pos.side === 'LONG') {
              unrealizedPnl = (currentPrice - pos.entry_price) * pos.quantity;
            } else {
              unrealizedPnl = (pos.entry_price - currentPrice) * pos.quantity;
            }
          }

          const roe = pos.margin > 0 ? (unrealizedPnl / pos.margin) * 100 : 0;
          const pnlColor = unrealizedPnl >= 0 ? 'text-green-400' : 'text-red-400';
          const sideColor = pos.side === 'LONG' ? 'bg-green-600' : 'bg-red-600';

          return (
            <div
              key={pos.id}
              className="flex items-center justify-between bg-gray-700 rounded-lg p-3"
            >
              <div className="flex items-center space-x-3">
                <span className={`px-2 py-1 ${sideColor} rounded text-xs font-bold`}>
                  {pos.side} {pos.leverage}x
                </span>
                <div>
                  <span className="font-semibold">{pos.quantity}</span>
                  <span className="text-gray-400 text-sm ml-1">
                    @ ${formatPrice(pos.entry_price)}
                  </span>
                </div>
              </div>
              <div className="text-right">
                <p className={`font-bold ${pnlColor}`}>
                  {unrealizedPnl >= 0 ? '+' : ''}${formatPrice(unrealizedPnl)}
                </p>
                <p className={`text-sm ${pnlColor}`}>
                  {roe >= 0 ? '+' : ''}{roe.toFixed(2)}%
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default FuturesTrading;