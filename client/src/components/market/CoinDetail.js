// client/src/components/market/CoinDetail.js
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMarket } from '../../contexts/MarketContext';
import { useAuth } from '../../contexts/AuthContext';
import axios from '../../api/axios';

const CoinDetail = () => {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const { coins, realtimePrices } = useMarket();
  const { isAuthenticated } = useAuth();
  const [coin, setCoin] = useState(null);
  const [historicalData, setHistoricalData] = useState([]);

  useEffect(() => {
    const foundCoin = coins.find((c) => c.symbol === symbol);
    if (foundCoin) {
      setCoin(foundCoin);
      fetchHistoricalData(symbol);
    }
  }, [symbol, coins]);

  const fetchHistoricalData = async (sym) => {
    try {
      const response = await axios.get(`/api/v1/market/historical/${sym}`);
      setHistoricalData(response.data);
    } catch (error) {
      console.error('Failed to fetch historical data:', error);
    }
  };

  if (!coin) {
    return <div className="text-center py-20">코인 정보를 불러오는 중...</div>;
  }

  const currentPrice = realtimePrices[symbol] || 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="w-16 h-16 rounded-full flex items-center justify-center text-3xl font-bold" style={{ backgroundColor: coin.color }}>
            {coin.icon}
          </div>
          <div>
            <h1 className="text-3xl font-bold">{coin.name}</h1>
            <p className="text-gray-400">{coin.symbol}</p>
          </div>
        </div>
        {isAuthenticated && (
          <button onClick={() => navigate(`/trade/${symbol}`)} className="px-6 py-3 bg-accent hover:bg-teal-600 rounded-lg font-semibold">
            거래하기
          </button>
        )}
      </div>

      <div className="bg-gray-800 rounded-lg p-6">
        <div className="text-4xl font-bold mb-2">${currentPrice.toLocaleString('ko-KR')}</div>
      </div>

      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">최근 24시간 데이터</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-3 px-4">시간</th>
                <th className="text-right py-3 px-4">시가</th>
                <th className="text-right py-3 px-4">고가</th>
                <th className="text-right py-3 px-4">저가</th>
                <th className="text-right py-3 px-4">종가</th>
              </tr>
            </thead>
            <tbody>
              {historicalData.slice(0, 10).map((data, index) => (
                <tr key={index} className="border-b border-gray-700">
                  <td className="py-3 px-4">{new Date(data.timestamp).toLocaleString('ko-KR')}</td>
                  <td className="text-right py-3 px-4">${data.open.toFixed(2)}</td>
                  <td className="text-right py-3 px-4 text-green-400">${data.high.toFixed(2)}</td>
                  <td className="text-right py-3 px-4 text-red-400">${data.low.toFixed(2)}</td>
                  <td className="text-right py-3 px-4">${data.close.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default CoinDetail;