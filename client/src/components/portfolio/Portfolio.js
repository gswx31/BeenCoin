// client/src/components/portfolio/Portfolio.js
import React, { useState, useEffect } from 'react';
import axios from '../../api/axios';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { toast } from 'react-toastify';

const Portfolio = () => {
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    fetchPortfolio();
    const interval = setInterval(fetchPortfolio, 5000);
    return () => clearInterval(interval);
  }, [isAuthenticated, navigate]);

  const fetchPortfolio = async () => {
    try {
      const response = await axios.get('/api/v1/account/');
      setPortfolio(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Portfolio fetch error:', error);
      toast.error('포트폴리오 조회 실패');
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-accent"></div>
      </div>
    );
  }

  if (!portfolio) {
    return (
      <div className="text-center text-gray-400 py-8">
        <p>포트폴리오를 불러올 수 없습니다</p>
      </div>
    );
  }

  const profitColor = portfolio.total_profit >= 0 ? 'text-green-400' : 'text-red-400';
  const profitSign = portfolio.total_profit >= 0 ? '+' : '';

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">내 포트폴리오</h1>

      {/* 계정 요약 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gray-800 rounded-lg p-6">
          <p className="text-sm text-gray-400 mb-2">총 자산</p>
          <p className="text-3xl font-bold text-accent">
            ${portfolio.total_value?.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}
          </p>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <p className="text-sm text-gray-400 mb-2">보유 현금</p>
          <p className="text-3xl font-bold">
            ${portfolio.balance?.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}
          </p>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <p className="text-sm text-gray-400 mb-2">실현 손익</p>
          <p className={`text-3xl font-bold ${profitColor}`}>
            {profitSign}${portfolio.total_profit?.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}
          </p>
          <p className={`text-sm ${profitColor}`}>
            {profitSign}{portfolio.profit_rate?.toFixed(2)}%
          </p>
        </div>
      </div>

      {/* 보유 코인 */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">보유 코인</h2>
        {portfolio.positions && portfolio.positions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-700">
                  <th className="pb-3">코인</th>
                  <th className="pb-3 text-right">보유량</th>
                  <th className="pb-3 text-right">평균 매수가</th>
                  <th className="pb-3 text-right">현재가</th>
                  <th className="pb-3 text-right">평가액</th>
                  <th className="pb-3 text-right">평가손익</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.positions.map((pos, idx) => {
                  const profitColor = pos.unrealized_profit >= 0 ? 'text-green-400' : 'text-red-400';
                  const profitSign = pos.unrealized_profit >= 0 ? '+' : '';
                  const profitRate = ((pos.current_price - pos.average_price) / pos.average_price * 100).toFixed(2);

                  return (
                    <tr key={idx} className="border-b border-gray-700 hover:bg-gray-700">
                      <td className="py-4 font-semibold">{pos.symbol.replace('USDT', '')}</td>
                      <td className="py-4 text-right">{pos.quantity.toFixed(8)}</td>
                      <td className="py-4 text-right">${pos.average_price.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}</td>
                      <td className="py-4 text-right">${pos.current_price.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}</td>
                      <td className="py-4 text-right font-semibold">${pos.current_value.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}</td>
                      <td className={`py-4 text-right font-semibold ${profitColor}`}>
                        {profitSign}${pos.unrealized_profit.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}
                        <br />
                        <span className="text-xs">({profitSign}{profitRate}%)</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center text-gray-400 py-8">
            <p>보유 중인 코인이 없습니다</p>
            <button
              onClick={() => navigate('/')}
              className="mt-4 px-6 py-2 bg-accent text-white rounded-lg hover:bg-teal-600"
            >
              거래 시작하기
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Portfolio;