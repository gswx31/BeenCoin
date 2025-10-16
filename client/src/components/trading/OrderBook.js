import React, { useState, useEffect } from 'react';

const OrderBook = ({ symbol, currentPrice }) => {
  const [orders, setOrders] = useState({ bids: [], asks: [] });

  useEffect(() => {
    generateOrderBook();
    const interval = setInterval(generateOrderBook, 2000);
    return () => clearInterval(interval);
  }, [symbol, currentPrice]);

  const generateOrderBook = () => {
    const basePrice = currentPrice > 0 ? currentPrice : 50000;  // ✅ 실제 가격 사용
    const spread = basePrice * 0.0002;  // 0.02% 스프레드
    
    const bids = Array.from({ length: 10 }, (_, i) => ({
      price: basePrice - spread - (i * spread),
      quantity: (Math.random() * 2 + 0.1).toFixed(6),
    }));
    
    const asks = Array.from({ length: 10 }, (_, i) => ({
      price: basePrice + spread + (i * spread),
      quantity: (Math.random() * 2 + 0.1).toFixed(6),
    }));
    
    setOrders({ bids, asks });
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4">호가창</h2>
      <div className="space-y-4">
        <div>
          <div className="text-sm text-gray-400 mb-2">매도 호가</div>
          <div className="space-y-1">
            {orders.asks.slice(0, 5).reverse().map((order, idx) => (
              <div key={idx} className="flex justify-between text-sm py-1 hover:bg-gray-700 transition-colors">
                <span className="text-red-400 font-medium">${order.price.toLocaleString('en-US', { maximumFractionDigits: 2 })}</span>
                <span className="text-gray-400">{order.quantity}</span>
              </div>
            ))}
          </div>
        </div>
        
        {/* ✅ 현재가 표시 */}
        <div className="border-y border-gray-700 py-2 text-center">
          <span className="text-accent font-bold text-lg">
            ${currentPrice > 0 ? currentPrice.toLocaleString('en-US', { maximumFractionDigits: 2 }) : '---'}
          </span>
        </div>
        
        <div>
          <div className="text-sm text-gray-400 mb-2">매수 호가</div>
          <div className="space-y-1">
            {orders.bids.slice(0, 5).map((order, idx) => (
              <div key={idx} className="flex justify-between text-sm py-1 hover:bg-gray-700 transition-colors">
                <span className="text-green-400 font-medium">${order.price.toLocaleString('en-US', { maximumFractionDigits: 2 })}</span>
                <span className="text-gray-400">{order.quantity}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default OrderBook;