// client/src/components/trading/RecentTrades.js
import React, { useState, useEffect } from 'react';

const RecentTrades = ({ symbol }) => {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTrades();
    const interval = setInterval(fetchTrades, 2000); // 2초마다 갱신
    return () => clearInterval(interval);
  }, [symbol]);

  const fetchTrades = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/market/trades/${symbol}?limit=20`);
      
      if (!response.ok) throw new Error('Failed to fetch trades');
      
      const data = await response.json();
      
      const formattedTrades = data.map(trade => ({
        id: trade.id,
        price: trade.price,
        quantity: trade.quantity,
        time: new Date(trade.time).toLocaleTimeString('ko-KR', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        }),
        side: trade.isBuyerMaker ? 'SELL' : 'BUY' // buyer가 maker면 매도 체결
      }));
      
      setTrades(formattedTrades);
      setLoading(false);
    } catch (error) {
      console.error('체결 내역 조회 실패:', error);
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">실시간 체결</h2>
        <span className="text-xs text-gray-500">바이낸스 실시간</span>
      </div>
      
      <div className="space-y-2">
        <div className="grid grid-cols-3 text-sm text-gray-400 pb-2 border-b border-gray-700">
          <span>가격(USDT)</span>
          <span className="text-right">수량</span>
          <span className="text-right">시간</span>
        </div>
        
        <div className="space-y-1 max-h-[400px] overflow-y-auto">
          {loading ? (
            <div className="text-center text-gray-400 py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent mx-auto"></div>
            </div>
          ) : trades.length > 0 ? (
            trades.map((trade) => (
              <div key={trade.id} className="grid grid-cols-3 text-sm py-1 hover:bg-gray-700 transition-colors">
                <span className={`font-medium ${trade.side === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>
                  ${trade.price.toLocaleString('en-US', { maximumFractionDigits: 2 })}
                </span>
                <span className="text-right text-gray-300">
                  {trade.quantity.toFixed(6)}
                </span>
                <span className="text-right text-gray-400 text-xs">
                  {trade.time}
                </span>
              </div>
            ))
          ) : (
            <div className="text-center text-gray-400 py-8">
              체결 내역이 없습니다
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RecentTrades;