// client/src/components/trading/FuturesTrading.js
// =============================================================================
// 선물 거래 메인 컴포넌트 - 대기 주문 추가
// =============================================================================
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useMarket } from '../../contexts/MarketContext';
import { useFutures } from '../../contexts/FuturesContext';
import { formatPrice } from '../../utils/formatPrice';
import { toast } from 'react-toastify';
import TradingChart from './TradingChart';
import FuturesOrderForm from './FuturesOrderForm';
import OrderBook from './OrderBook';
import RecentTrades from './RecentTrades';
import PositionsList from './PositionsList';
import PendingOrders from './PendingOrders';  // ⭐ NEW

const FuturesTrading = () => {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { coins, realtimePrices, isConnected, loading: marketLoading } = useMarket();
  const { account, positions, fetchPositions } = useFutures();

  const [coin, setCoin] = useState(null);
  const [currentPrice, setCurrentPrice] = useState(0);
  const [priceChange, setPriceChange] = useState(0);
  const [priceAnimation, setPriceAnimation] = useState('');

  // 인증 체크
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: `/futures/${symbol}` } });
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
        setCoin({
          symbol,
          name: symbol.replace('USDT', ''),
          icon: '₿',
          color: '#F7931A',
        });
      }
    }
  }, [symbol, coins]);

  // 실시간 가격 업데이트 + 애니메이션
  useEffect(() => {
    if (realtimePrices[symbol]) {
      const newPrice = realtimePrices[symbol];
      
      if (currentPrice > 0 && newPrice !== currentPrice) {
        if (newPrice > currentPrice) {
          setPriceAnimation('up');
          playTradeSound('buy');
          showPriceFlash('green');
        } else if (newPrice < currentPrice) {
          setPriceAnimation('down');
          playTradeSound('sell');
          showPriceFlash('red');
        }
        
        setTimeout(() => setPriceAnimation(''), 500);
      }
      
      setCurrentPrice(newPrice);
    }
  }, [realtimePrices, symbol, currentPrice]);

  // 체결 사운드
  const playTradeSound = (type) => {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.value = type === 'buy' ? 800 : 600;
      oscillator.type = 'sine';
      
      gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.1);
    } catch (error) {
      console.warn('사운드 재생 실패:', error);
    }
  };

  // 화면 플래시
  const showPriceFlash = (color) => {
    try {
      const flashOverlay = document.createElement('div');
      flashOverlay.className = 'fixed inset-0 pointer-events-none z-50 transition-opacity duration-300';
      flashOverlay.style.backgroundColor = color === 'green' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)';
      flashOverlay.style.opacity = '1';
      
      document.body.appendChild(flashOverlay);
      
      setTimeout(() => {
        flashOverlay.style.opacity = '0';
        setTimeout(() => document.body.removeChild(flashOverlay), 300);
      }, 100);
    } catch (error) {
      console.warn('플래시 효과 실패:', error);
    }
  };

  // 포지션 새로고침
  useEffect(() => {
    if (isAuthenticated) {
      fetchPositions();
      const interval = setInterval(fetchPositions, 30000);
      return () => clearInterval(interval);
    }
  }, [isAuthenticated, fetchPositions]);

  // 현재 심볼의 오픈 포지션
  const symbolPositions = positions.filter(
    (pos) => pos.symbol === symbol && pos.status === 'OPEN'
  );

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
        priceAnimation={priceAnimation}
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

      {/* 중단 그리드 - 대기 주문 (⭐ NEW) */}
      <PendingOrders symbol={symbol} />

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
const TradingHeader = ({ coin, currentPrice, priceChange, priceAnimation, isConnected, account }) => {
  const isPositive = priceChange >= 0;

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          {coin && (
            <div
              className="w-14 h-14 rounded-full flex items-center justify-center text-2xl font-bold shadow-lg"
              style={{ backgroundColor: coin.color || '#4fd1c5' }}
            >
              {coin.icon || coin.symbol?.charAt(0)}
            </div>
          )}
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-2xl font-bold">{coin?.name || 'Loading...'}</h1>
              <span className="text-gray-400">{coin?.symbol}</span>
              <span className="px-2 py-1 bg-purple-600 rounded text-xs font-semibold animate-pulse">
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
          <p 
            className={`text-4xl font-bold transition-all duration-300 ${
              priceAnimation === 'up' 
                ? 'text-green-400 scale-110' 
                : priceAnimation === 'down' 
                ? 'text-red-400 scale-110' 
                : 'text-accent scale-100'
            }`}
          >
            ${currentPrice > 0 ? formatPrice(currentPrice) : '---'}
          </p>
          <p className={`text-sm mt-1 ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
            {isPositive ? '▲' : '▼'} {isPositive ? '+' : ''}{priceChange.toFixed(2)}% (24h)
          </p>
        </div>

        {/* 계좌 정보 */}
        <div className="text-right bg-gray-900 px-4 py-3 rounded-lg">
          <p className="text-sm text-gray-400 mb-1">계좌 잔고</p>
          <p className="text-2xl font-bold text-yellow-400">
            ${account ? formatPrice(account.balance) : '0.00'}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            증거금: ${account ? formatPrice(account.margin_used) : '0.00'}
          </p>
        </div>
      </div>
    </div>
  );
};

// =============================================================================
// 현재 포지션 컴포넌트
// =============================================================================
const CurrentPositions = ({ positions, currentPrice }) => {
  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4">이 종목의 오픈 포지션</h2>
      <div className="space-y-3">
        {positions.map((position) => {
          const pnl = position.side === 'LONG'
            ? (currentPrice - position.entry_price) * position.quantity
            : (position.entry_price - currentPrice) * position.quantity;
          
          const roe = (pnl / position.margin) * 100;
          const isProfit = pnl >= 0;

          return (
            <div
              key={position.id}
              className={`p-4 rounded-lg border-2 ${
                position.side === 'LONG' 
                  ? 'bg-green-900/20 border-green-500/50' 
                  : 'bg-red-900/20 border-red-500/50'
              }`}
            >
              <div className="flex justify-between items-center">
                <div>
                  <span className={`font-bold text-lg ${
                    position.side === 'LONG' ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {position.side} {position.leverage}x
                  </span>
                  <p className="text-sm text-gray-400 mt-1">
                    수량: {parseFloat(position.quantity).toFixed(6)} | 
                    진입가: ${formatPrice(position.entry_price)}
                  </p>
                </div>
                <div className="text-right">
                  <p className={`text-2xl font-bold ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
                    {isProfit ? '+' : ''}${formatPrice(pnl)}
                  </p>
                  <p className={`text-sm ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
                    {isProfit ? '+' : ''}{roe.toFixed(2)}%
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default FuturesTrading;