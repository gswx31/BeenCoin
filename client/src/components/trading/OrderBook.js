// client/src/components/trading/OrderBook.js
// =============================================================================
// 개선된 호가창 컴포넌트
// - 실시간 체결 강조
// - 수량 막대 그래프
// - 현재가 중심 배치
// =============================================================================
import React, { useState, useEffect } from 'react';
import { formatPrice } from '../../utils/formatPrice';

const OrderBook = ({ symbol, currentPrice }) => {
  const [orders, setOrders] = useState({ bids: [], asks: [] });
  const [lastTrade, setLastTrade] = useState(null);
  const [highlightedPrice, setHighlightedPrice] = useState(null);

  useEffect(() => {
    generateOrderBook();
    const interval = setInterval(generateOrderBook, 1500); // 1.5초마다 업데이트
    return () => clearInterval(interval);
  }, [symbol, currentPrice]);

  const generateOrderBook = () => {
    const basePrice = currentPrice > 0 ? currentPrice : 50000;
    const spread = basePrice * 0.0001; // 0.01% 스프레드
    
    // 매수 호가 (현재가보다 낮음)
    const bids = Array.from({ length: 15 }, (_, i) => {
      const price = basePrice - spread * (i + 1);
      const quantity = (Math.random() * 5 + 0.5).toFixed(6);
      return { price, quantity: parseFloat(quantity) };
    });
    
    // 매도 호가 (현재가보다 높음)
    const asks = Array.from({ length: 15 }, (_, i) => {
      const price = basePrice + spread * (i + 1);
      const quantity = (Math.random() * 5 + 0.5).toFixed(6);
      return { price, quantity: parseFloat(quantity) };
    }).reverse();
    
    setOrders({ bids, asks });

    // 랜덤 체결 효과
    if (Math.random() > 0.7) {
      const isBuy = Math.random() > 0.5;
      const tradePrice = isBuy 
        ? asks[Math.floor(Math.random() * 5)].price
        : bids[Math.floor(Math.random() * 5)].price;
      
      setHighlightedPrice(tradePrice);
      setLastTrade({ price: tradePrice, side: isBuy ? 'buy' : 'sell' });
      
      // 강조 효과 제거
      setTimeout(() => setHighlightedPrice(null), 800);
    }
  };

  // 최대 수량 계산 (막대 그래프용)
  const maxQuantity = Math.max(
    ...orders.bids.map(o => o.quantity),
    ...orders.asks.map(o => o.quantity)
  );

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">호가창</h2>
        {lastTrade && (
          <div className={`text-xs px-2 py-1 rounded ${
            lastTrade.side === 'buy' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
          }`}>
            {lastTrade.side === 'buy' ? '▲ 체결' : '▼ 체결'}
          </div>
        )}
      </div>

      <div className="space-y-1">
        {/* 매도 호가 (위에서 아래로) */}
        <div className="space-y-0.5">
          <div className="text-xs text-gray-500 mb-2 flex justify-between px-2">
            <span>가격(USDT)</span>
            <span>수량</span>
          </div>
          
          {orders.asks.slice(0, 10).map((order, idx) => {
            const barWidth = (order.quantity / maxQuantity) * 100;
            const isHighlighted = highlightedPrice === order.price;
            
            return (
              <div
                key={`ask-${idx}`}
                className={`relative flex justify-between text-sm py-1.5 px-2 rounded transition-all duration-300 ${
                  isHighlighted 
                    ? 'bg-red-500/30 scale-105 shadow-lg shadow-red-500/50' 
                    : 'hover:bg-gray-700/50'
                }`}
              >
                {/* 수량 막대 */}
                <div 
                  className="absolute right-0 top-0 bottom-0 bg-red-900/20 transition-all"
                  style={{ width: `${barWidth}%` }}
                />
                
                {/* 가격과 수량 */}
                <span className="relative z-10 text-red-400 font-semibold">
                  {formatPrice(order.price)}
                </span>
                <span className="relative z-10 text-gray-300">
                  {order.quantity.toFixed(4)}
                </span>
              </div>
            );
          })}
        </div>

        {/* 현재가 표시 (중앙) */}
        <div className="border-y-2 border-accent/50 py-3 my-2 text-center bg-accent/10">
          <div className="text-xs text-gray-400 mb-1">현재가</div>
          <span className="text-accent font-bold text-xl tracking-wide">
            {currentPrice > 0 ? formatPrice(currentPrice) : '---'}
          </span>
          <div className="text-xs text-gray-500 mt-1">
            스프레드: {currentPrice > 0 ? formatPrice(currentPrice * 0.0001) : '---'}
          </div>
        </div>

        {/* 매수 호가 (위에서 아래로) */}
        <div className="space-y-0.5">
          {orders.bids.slice(0, 10).map((order, idx) => {
            const barWidth = (order.quantity / maxQuantity) * 100;
            const isHighlighted = highlightedPrice === order.price;
            
            return (
              <div
                key={`bid-${idx}`}
                className={`relative flex justify-between text-sm py-1.5 px-2 rounded transition-all duration-300 ${
                  isHighlighted 
                    ? 'bg-green-500/30 scale-105 shadow-lg shadow-green-500/50' 
                    : 'hover:bg-gray-700/50'
                }`}
              >
                {/* 수량 막대 */}
                <div 
                  className="absolute right-0 top-0 bottom-0 bg-green-900/20 transition-all"
                  style={{ width: `${barWidth}%` }}
                />
                
                {/* 가격과 수량 */}
                <span className="relative z-10 text-green-400 font-semibold">
                  {formatPrice(order.price)}
                </span>
                <span className="relative z-10 text-gray-300">
                  {order.quantity.toFixed(4)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* 호가창 설명 */}
      <div className="mt-4 pt-4 border-t border-gray-700">
        <div className="text-xs text-gray-500 space-y-1">
          <div className="flex justify-between">
            <span>총 매도 수량:</span>
            <span className="text-red-400">
              {orders.asks.reduce((sum, o) => sum + o.quantity, 0).toFixed(4)}
            </span>
          </div>
          <div className="flex justify-between">
            <span>총 매수 수량:</span>
            <span className="text-green-400">
              {orders.bids.reduce((sum, o) => sum + o.quantity, 0).toFixed(4)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OrderBook;