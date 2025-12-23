// client/src/components/trading/RecentTrades.js
import React, { useState, useEffect } from 'react';

const RecentTrades = ({ symbol }) => {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTrades();
    const interval = setInterval(fetchTrades, 2000);
    return () => clearInterval(interval);
  }, [symbol]);

  const fetchTrades = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/market/trades/${symbol}?limit=20`);
      
      if (!response.ok) throw new Error('Failed to fetch trades');
      
      const data = await response.json();
      
      // 🆕 수정: API 응답 구조에 맞게 qty → quantity 매핑
      const formattedTrades = (data || []).map(trade => {
        // price와 qty가 문자열로 오는 경우 처리
        const price = parseFloat(trade?.price) || 0;
        const quantity = parseFloat(trade?.qty) || 0; // 🆕 qty로 수정
        const time = trade?.time ? new Date(trade.time) : new Date();
        
        return {
          id: trade?.id || Date.now() + Math.random(),
          price: price,
          quantity: quantity,
          time: time.toLocaleTimeString('ko-KR', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
          }),
          // 🆕 API에 맞게 isBuyerMaker 필드 확인 필요
          side: trade?.isBuyerMaker === true ? 'SELL' : 'BUY'
        };
      });
      
      setTrades(formattedTrades);
      setLoading(false);
    } catch (error) {
      console.error('체결 내역 조회 실패:', error);
      setTrades([]);
      setLoading(false);
    }
  };

  // 안전한 숫자 포맷팅 함수
  const formatPrice = (price) => {
    const num = Number(price);
    if (isNaN(num) || num === 0) return '0.00';
    return num.toLocaleString('en-US', { 
      minimumFractionDigits: 2,
      maximumFractionDigits: 2 
    });
  };

  // 안전한 수량 포맷팅 함수
  const formatQuantity = (quantity) => {
    const num = Number(quantity);
    if (isNaN(num) || num === 0) return '0.000000';
    return num.toFixed(6);
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
                  ${formatPrice(trade.price)}
                </span>
                <span className="text-right text-gray-300">
                  {formatQuantity(trade.quantity)}
                </span>
                <span className="text-right text-gray-400 text-xs">
                  {trade.time || '--:--:--'}
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