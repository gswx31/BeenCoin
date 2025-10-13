// client/src/components/trading/RecentTrades.js
import React, { useState, useEffect } from 'react';

const RecentTrades = ({ symbol }) => {
  const [trades, setTrades] = useState([]);

  useEffect(() => {
    generateMockTrades();
    const interval = setInterval(() => {
      generateMockTrades();
    }, 3000);
    return () => clearInterval(interval);
  }, [symbol]);

  const generateMockTrades = () => {
    const newTrades = Array.from({ length: 15 }, () => ({
      price: (50000 + (Math.random() - 0.5) * 1000).toFixed(2),
      quantity: (Math.random() * 0.5).toFixed(4),
      time: new Date().toLocaleTimeString('ko-KR'),
      side: Math.random() > 0.5 ? 'BUY' : 'SELL',
    }));
    setTrades(newTrades);
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4">최근 체결</h2>
      <div className="space-y-2">
        <div className="grid grid-cols-3 text-sm text-gray-400 pb-2 border-b border-gray-700">
          <span>가격</span>
          <span className="text-right">수량</span>
          <span className="text-right">시간</span>
        </div>
        <div className="space-y-1 max-h-[400px] overflow-y-auto">
          {trades.map((trade, idx) => (
            <div key={idx} className="grid grid-cols-3 text-sm">
              <span className={trade.side === 'BUY' ? 'text-green-400' : 'text-red-400'}>
                ${parseFloat(trade.price).toLocaleString()}
              </span>
              <span className="text-right text-gray-300">{trade.quantity}</span>
              <span className="text-right text-gray-400">{trade.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default RecentTrades;