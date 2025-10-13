// client/src/components/trading/OrderBook.js
import React, { useState, useEffect } from 'react';

const OrderBook = ({ symbol }) => {
  const [orders, setOrders] = useState({ bids: [], asks: [] });

  useEffect(() => {
    generateMockOrderBook();
    const interval = setInterval(generateMockOrderBook, 2000);
    return () => clearInterval(interval);
  }, [symbol]);

  const generateMockOrderBook = () => {
    const basePrice = 50000;
    const bids = Array.from({ length: 10 }, (_, i) => ({
      price: basePrice - (i * 10),
      quantity: (Math.random() * 2).toFixed(4),
    }));
    const asks = Array.from({ length: 10 }, (_, i) => ({
      price: basePrice + (i * 10),
      quantity: (Math.random() * 2).toFixed(4),
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
              <div key={idx} className="flex justify-between text-sm">
                <span className="text-red-400">${order.price.toLocaleString()}</span>
                <span className="text-gray-400">{order.quantity}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="border-t border-gray-700 pt-4">
          <div className="text-sm text-gray-400 mb-2">매수 호가</div>
          <div className="space-y-1">
            {orders.bids.slice(0, 5).map((order, idx) => (
              <div key={idx} className="flex justify-between text-sm">
                <span className="text-green-400">${order.price.toLocaleString()}</span>
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