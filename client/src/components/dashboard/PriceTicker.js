// client/src/components/dashboard/PriceTicker.js
import React from 'react';

const PriceTicker = ({ coins }) => {
  return (
    <div className="bg-gray-800 rounded-lg p-4 overflow-hidden">
      <div className="flex space-x-6 overflow-x-auto scrollbar-hide">
        {coins.map((coin) => {
          const isPositive = coin.change >= 0;
          return (
            <div key={coin.symbol} className="flex items-center space-x-3 min-w-[200px]">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold"
                style={{ backgroundColor: coin.color }}
              >
                {coin.icon}
              </div>
              <div>
                <div className="text-sm font-semibold">{coin.symbol.replace('USDT', '')}</div>
                <div className="flex items-center space-x-2">
                  <span className="text-lg font-bold">
                    ${coin.currentPrice?.toLocaleString('ko-KR') || '0'}
                  </span>
                  <span className={`text-sm ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                    {isPositive ? '+' : ''}{coin.change.toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default PriceTicker;