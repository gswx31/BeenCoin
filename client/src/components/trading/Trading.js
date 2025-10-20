// client/src/components/trading/Trading.js
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMarket } from '../../contexts/MarketContext';
import { useAuth } from '../../contexts/AuthContext';
import { formatPrice } from '../../utils/formatPrice';
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
  const [orderType, setOrderType] = useState('MARKET');

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
      {/* 코인 헤더 */}
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div 
              className="w-16 h-16 rounded-full flex items-center justify-center text-3xl font-bold"
              style={{ backgroundColor: coin.color }}
            >
              {coin.icon}
            </div>
            <div>
              <h1 className="text-3xl font-bold">{coin.name}</h1>
              <p className="text-gray-400">{coin.symbol}</p>
            </div>
          </div>
          
          <div className="text-right">
            <p className="text-sm text-gray-400 mb-1">현재가</p>
            <p className="text-4xl font-bold text-accent">
              ${currentPrice > 0 ? formatPrice(currentPrice) : 'Loading...'}
            </p>
            <p className={`text-sm mt-1 ${parseFloat(coin.change) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {parseFloat(coin.change) >= 0 ? '+' : ''}{parseFloat(coin.change).toFixed(2)}% (24h)
            </p>
          </div>
        </div>
      </div>

      {/* 차트와 주문 폼 */}
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

      {/* 호가창과 최근 거래 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <OrderBook symbol={symbol} currentPrice={currentPrice} />
        <RecentTrades symbol={symbol} />
      </div>
    </div>
  );
};

export default Trading;