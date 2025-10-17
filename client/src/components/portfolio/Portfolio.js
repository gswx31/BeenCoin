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
    const interval = setInterval(fetchPortfolio, 5000); // 5초마다 갱신
    return () => clearInterval(interval);
  }, [isAuthenticated, navigate]);

  const fetchPortfolio = async () => {
    try {
      const response = await axios.get('/api/v1/account/');
      setPortfolio(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Portfolio fetch error:', error);
      if (error.response?.status !== 401) {
        toast.error('포트폴리오 조회 실패');
      }
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
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-gray-800 rounded-lg p-6">
          <p className="text-sm text-gray-400 mb-2">총 자산</p>
          <p className="text-2xl font-bold text-accent">
            ${portfolio.total_value?.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}
          </p>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <p className="text-sm text-gray-400 mb-2">보유 현금</p>
          <p className="text-2xl font-bold">
            ${portfolio.balance?.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}
          </p>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <p className="text-sm text-gray-400 mb-2">실현 손익</p>
          <p className={`text-2xl font-bold ${profitColor}`}>
            {profitSign}${Math.abs(portfolio.total_profit)?.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}
          </p>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <p className="text-sm text-gray-400 mb-2">수익률</p>
          <p className={`text-2xl font-bold ${profitColor}`}>
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
                <tr className="text-gray-400 border-b border-gray-700">
                  <th className="text-left py-3 px-4">코인</th>
                  <th className="text-right py-3 px-4">보유량</th>
                  <th className="text-right py-3 px-4">미체결</th>
                  <th className="text-right py-3 px-4">주문가능</th>
                  <th className="text-right py-3 px-4">평균가</th>
                  <th className="text-right py-3 px-4">현재가</th>
                  <th className="text-right py-3 px-4">평가액</th>
                  <th className="text-right py-3 px-4">손익</th>
                  <th className="text-right py-3 px-4">수익률</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.positions.map((pos) => {
                  const profitColor = pos.unrealized_profit >= 0 
                    ? 'text-green-400' 
                    : 'text-red-400';
                  const profitSign = pos.unrealized_profit >= 0 ? '+' : '';
                  
                  return (
                    <tr 
                      key={pos.id} 
                      className="border-b border-gray-700 hover:bg-gray-750 transition-colors"
                    >
                      <td className="py-4 px-4">
                        <div className="font-semibold text-white">
                          {pos.symbol.replace('USDT', '')}
                        </div>
                        <div className="text-xs text-gray-500">{pos.symbol}</div>
                      </td>
                      <td className="text-right py-4 px-4 text-white">
                        {pos.quantity.toFixed(8)}
                      </td>
                      <td className="text-right py-4 px-4 text-yellow-400">
                        {pos.locked_quantity.toFixed(8)}
                      </td>
                      <td className="text-right py-4 px-4 text-green-400 font-semibold">
                        {pos.available_quantity.toFixed(8)}
                      </td>
                      <td className="text-right py-4 px-4 text-gray-300">
                        ${pos.average_price.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}
                      </td>
                      <td className="text-right py-4 px-4 text-white">
                        ${pos.current_price.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}
                      </td>
                      <td className="text-right py-4 px-4 text-white font-semibold">
                        ${pos.current_value.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}
                      </td>
                      <td className={`text-right py-4 px-4 font-semibold ${profitColor}`}>
                        {profitSign}${Math.abs(pos.unrealized_profit).toLocaleString('ko-KR', { maximumFractionDigits: 2 })}
                      </td>
                      <td className={`text-right py-4 px-4 font-bold ${profitColor}`}>
                        {profitSign}{pos.profit_rate.toFixed(2)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12">
            <div className="text-gray-500 mb-4">
              <svg 
                className="w-16 h-16 mx-auto mb-4" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" 
                />
              </svg>
              <p className="text-lg">보유 중인 코인이 없습니다</p>
              <p className="text-sm mt-2">거래를 시작해보세요!</p>
            </div>
            <button
              onClick={() => navigate('/trading')}
              className="bg-accent hover:bg-accent-dark text-dark font-semibold px-6 py-3 rounded-lg transition-colors"
            >
              거래 시작하기
            </button>
          </div>
        )}
      </div>

      {/* 포트폴리오 설명 */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-3">포트폴리오 용어 설명</h3>
        <div className="space-y-2 text-sm text-gray-400">
          <div className="flex">
            <span className="font-semibold text-white w-32">보유량:</span>
            <span>현재 보유하고 있는 총 코인 수량</span>
          </div>
          <div className="flex">
            <span className="font-semibold text-yellow-400 w-32">미체결:</span>
            <span>현재 대기 중인 매도 주문에 묶여있는 수량</span>
          </div>
          <div className="flex">
            <span className="font-semibold text-green-400 w-32">주문가능:</span>
            <span>즉시 매도 주문을 낼 수 있는 수량 (보유량 - 미체결)</span>
          </div>
          <div className="flex">
            <span className="font-semibold text-white w-32">평균가:</span>
            <span>코인을 매수한 평균 가격</span>
          </div>
          <div className="flex">
            <span className="font-semibold text-white w-32">평가액:</span>
            <span>현재가 기준으로 계산한 보유 코인의 총 가치</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Portfolio;