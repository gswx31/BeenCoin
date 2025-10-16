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
  const [orderType, setOrderType] = useState('MARKET');  // ✅ 대문자

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

  if (!isAuthenticated) return null;
  if (!coin) return <div className="text-center text-gray-400">코인 정보 로딩 중...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-4">
        <div 
          className="w-12 h-12 rounded-full flex items-center justify-center text-2xl font-bold"
          style={{ backgroundColor: coin.color }}
        >
          {coin.icon}
        </div>
        <div>
          <h1 className="text-2xl font-bold">{coin.name} ({coin.symbol})</h1>
          <p className="text-3xl font-bold text-accent">
            ${currentPrice > 0 ? currentPrice.toLocaleString('ko-KR', { maximumFractionDigits: 2 }) : 'Loading...'}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <TradingChart symbol={symbol} />
        </div>
        <div>
          <OrderForm 
            symbol={symbol}
            currentPrice={currentPrice}
            orderType={orderType}
            onOrderTypeChange={setOrderType}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <OrderBook symbol={symbol} currentPrice={currentPrice} />
        <RecentTrades symbol={symbol} />
      </div>
    </div>
  );
};

export default Trading;