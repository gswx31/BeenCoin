// client/src/components/dashboard/Dashboard.js
// =============================================================================
// 대시보드 - 선물 거래 전용 마켓 대시보드
// =============================================================================
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useMarket } from '../../contexts/MarketContext';
import CoinCard from './CoinCard';

const Dashboard = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { coins, realtimePrices, isConnected, loading } = useMarket();

  // 실시간 가격을 포함한 코인 데이터
  const coinData = coins.map((coin) => ({
    ...coin,
    currentPrice: realtimePrices[coin.symbol] || parseFloat(coin.price) || 0,
  }));

  // 코인 카드 클릭 핸들러 - 선물 거래 페이지로 이동
  const handleCoinClick = (symbol) => {
    if (isAuthenticated) {
      navigate(`/futures/${symbol}`);
    } else {
      navigate('/login', { state: { from: `/futures/${symbol}` } });
    }
  };

  return (
    <div className="space-y-8">
      {/* 헤더 섹션 */}
      <div className="bg-gradient-to-r from-purple-900 via-gray-900 to-blue-900 rounded-lg p-8 text-center">
        <h1 className="text-4xl font-bold mb-3">
          BeenCoin 선물거래 플랫폼
        </h1>
        <p className="text-gray-300 mb-2">
          실시간 암호화폐 선물 거래 모의투자
        </p>
        <div className="flex items-center justify-center space-x-4 mt-4">
          {isConnected ? (
            <span className="flex items-center text-green-400 text-sm">
              <span className="w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse"></span>
              실시간 연결됨
            </span>
          ) : (
            <span className="flex items-center text-yellow-400 text-sm">
              <span className="w-2 h-2 bg-yellow-400 rounded-full mr-2"></span>
              연결 중...
            </span>
          )}
          <span className="text-purple-400 text-sm font-semibold">
            🔥 레버리지 최대 100배
          </span>
        </div>
      </div>

      {/* 주요 기능 소개 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <FeatureCard
          icon="📊"
          title="실시간 차트"
          description="1초부터 1주일까지 다양한 시간 단위 지원"
        />
        <FeatureCard
          icon="⚡"
          title="선물 거래"
          description="롱/숏 포지션, 레버리지 최대 100배"
        />
        <FeatureCard
          icon="💰"
          title="포트폴리오 관리"
          description="실시간 손익 계산 및 자동 청산"
        />
      </div>

      {/* 코인 리스트 */}
      <div>
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold">거래 가능 코인</h2>
          <span className="text-sm text-gray-400">
            {coinData.length}개 코인
          </span>
        </div>

        {!loading && coinData.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {coinData.map((coin) => (
              <div 
                key={coin.symbol}
                onClick={() => handleCoinClick(coin.symbol)}
                className="cursor-pointer transform hover:scale-105 transition-transform"
              >
                <CoinCard coin={coin} isFutures={true} />
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-20">
            <div className="w-16 h-16 border-4 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-400">코인 데이터를 불러오는 중...</p>
          </div>
        )}
      </div>

      {/* 비로그인 사용자용 CTA */}
      {!isAuthenticated && (
        <div className="text-center p-8 bg-gradient-to-r from-purple-900 to-blue-900 rounded-lg shadow-2xl">
          <h2 className="text-3xl font-bold mb-4">
            지금 가입하고 100만원으로 선물 거래 시작하기
          </h2>
          <p className="text-gray-300 mb-2">
            실시간 차트 분석, 레버리지 거래, 포트폴리오 관리까지
          </p>
          <p className="text-sm text-teal-300 mb-6">
            ⚠️ 모의투자 플랫폼입니다. 실제 돈이 거래되지 않습니다.
          </p>
          <div className="space-x-4">
            <a
              href="/register"
              className="inline-block px-8 py-3 bg-accent text-gray-900 rounded-lg hover:bg-accent/80 font-semibold text-lg transition-all shadow-lg hover:shadow-accent/50"
            >
              무료로 시작하기 🚀
            </a>
            <a
              href="/login"
              className="inline-block px-8 py-3 border-2 border-accent text-accent rounded-lg hover:bg-accent hover:text-gray-900 font-semibold text-lg transition-all"
            >
              로그인
            </a>
          </div>
        </div>
      )}

      {/* 주의사항 */}
      <div className="bg-yellow-900/20 border border-yellow-600/50 rounded-lg p-6">
        <h3 className="text-yellow-400 font-bold mb-2 flex items-center">
          <span className="text-2xl mr-2">⚠️</span>
          선물 거래 주의사항
        </h3>
        <ul className="text-sm text-gray-300 space-y-1 ml-8">
          <li>• 레버리지가 높을수록 청산 위험이 커집니다</li>
          <li>• 손실이 증거금을 초과하면 자동 청산됩니다</li>
          <li>• 이는 모의투자 플랫폼으로, 실제 돈이 거래되지 않습니다</li>
        </ul>
      </div>
    </div>
  );
};

// 기능 카드 컴포넌트
const FeatureCard = ({ icon, title, description }) => (
  <div className="bg-gray-800 rounded-lg p-6 text-center hover:bg-gray-750 transition-colors">
    <div className="text-4xl mb-3">{icon}</div>
    <h3 className="text-lg font-bold mb-2">{title}</h3>
    <p className="text-sm text-gray-400">{description}</p>
  </div>
);

export default Dashboard;