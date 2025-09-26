import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';

const Portfolio = () => {
  const [positions, setPositions] = useState([]);
  const token = localStorage.getItem('token');

  useEffect(() => {
    const fetchPortfolio = async () => {
      try {
        const response = await axios.get('/api/v1/account', {
          headers: { Authorization: `Bearer ${token}` },
        });
        setPositions(response.data.positions);
      } catch (error) {
        toast.error('포트폴리오 로드 실패');
      }
    };
    fetchPortfolio();
  }, [token]);

  return (
    <div className="max-w-4xl mx-auto mt-10 p-6 bg-white rounded-lg shadow-xl">
      <h2 className="text-2xl font-bold mb-4">포트폴리오</h2>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-gray-100">
              <th className="p-2 text-left">심볼</th>
              <th className="p-2 text-left">수량</th>
              <th className="p-2 text-left">평균 가격</th>
              <th className="p-2 text-left">현재 가치</th>
              <th className="p-2 text-left">미실현 수익</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((pos, index) => (
              <tr key={index} className="border-b">
                <td className="p-2">{pos.symbol}</td>
                <td className="p-2">{pos.quantity}</td>
                <td className="p-2">${pos.average_price.toFixed(2)}</td>
                <td className="p-2">${pos.current_value.toFixed(2)}</td>
                <td className={`p-2 ${pos.unrealized_profit > 0 ? 'text-green-600' : 'text-red-600'}`}>
                  ${pos.unrealized_profit.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <a href="/dashboard" className="mt-4 inline-block text-accent hover:underline">대시보드로 돌아가기</a>
    </div>
  );
};

export default Portfolio;
