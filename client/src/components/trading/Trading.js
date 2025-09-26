// client/src/components/trading/Trading.js
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMarket } from '../../contexts/MarketContext';
import { useAuth } from '../../contexts/AuthContext';
import TradingChart from './TradingChart';
import OrderForm from './OrderForm';
import OrderBook from './OrderBook';
import RecentTrades from './RecentTrades';

const Trading = () => {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const { coins, realtimePrices } = useMarket();
  const { isAuthenticated } = useAuth();
  const [coin, setCoin] = useState(null);
  const [currentPrice, setCurrentPrice] = useState(0);
  const [orderType, setOrderType] = useState('market');

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    const foundCoin = coins.find(c => c.symbol === symbol);
    if (foundCoin) {
      setCoin(foundCoin);
    }
  }, [symbol, coins, isAuthenticated, navigate]);

  useEffect(() => {
    if (symbol && realtimePrices[symbol]) {
      setCurrentPrice(realtimePrices[symbol]);
    }
  }, [symbol, realtimePrices]);

  if (!isAuthenticated) {
    return null;
  }

  if (!coin) {
    return <div className="text-center">코인 정보를 불러오는 중...</div>;
  }

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center space-x-4">
        <div 
          className="w-12 h-12 rounded-full flex items-center justify-center text-2xl font-bold"
          style={{ backgroundColor: coin.color }}
        >
          {coin.icon}
        </div>
        <div>
          <h1 className="text-2xl font-bold">
            {coin.name} ({coin.symbol})
          </h1>
          <p className="text-3xl font-bold text-accent">
            ${currentPrice.toLocaleString('ko-KR')}
          </p>
        </div>
      </div>

      {/* 메인 트레이딩 영역 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 차트 */}
        <div className="lg:col-span-2">
          <TradingChart symbol={symbol} />
        </div>

        {/* 주문 폼 */}
        <div>
          <OrderForm 
            symbol={symbol}
            currentPrice={currentPrice}
            orderType={orderType}
            onOrderTypeChange={setOrderType}
          />
        </div>
      </div>

      {/* 호가창 및 최근 체결 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <OrderBook symbol={symbol} />
        <RecentTrades symbol={symbol} />
      </div>
    </div>
  );
};

export default Trading;