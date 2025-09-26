// client/src/components/market/CoinCard.js
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const CoinCard = ({ coin }) => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  
  const isPositive = coin.change >= 0;
  const price = coin.currentPrice?.toLocaleString('ko-KR') || 'Loading...';

  const handleCardClick = () => {
    navigate(`/coin/${coin.symbol}`);
  };

  const handleTradeClick = (e) => {
    e.stopPropagation();
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    navigate(`/trade/${coin.symbol}`);
  };

  return (
    <div 
      className="bg-gray-800 rounded-lg p-4 hover:bg-gray-700 transition-colors cursor-pointer border border-gray-700"
      onClick={handleCardClick}
    >
      {/* 코인 헤더 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <div 
            className="w-10 h-10 rounded-full flex items-center justify-center text-xl font-bold"
            style={{ backgroundColor: coin.color }}
          >
            {coin.icon}
          </div>
          <div>
            <h3 className="font-semibold">{coin.symbol.replace('USDT', '')}</h3>
            <p className="text-sm text-gray-400">{coin.name}</p>
          </div>
        </div>
        <span className="text-xs px-2 py-1 bg-gray-700 rounded-full">{coin.category}</span>
      </div>

      {/* 가격 정보 */}
      <div className="space-y-2">
        <div className="text-2xl font-bold">${price}</div>
        <div className={`flex justify-between items-center ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
          <span>{isPositive ? '+' : ''}{coin.change.toFixed(2)}%</span>
          <span>24h</span>
        </div>
      </div>

      {/* 거래 버튼 */}
      <button 
        onClick={handleTradeClick}
        className="w-full mt-4 py-2 bg-accent text-white rounded-lg hover:bg-teal-600 transition-colors"
      >
        {isAuthenticated ? '거래하기' : '로그인 후 거래'}
      </button>
    </div>
  );
};

export default CoinCard;