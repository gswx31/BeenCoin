// client/src/components/dashboard/Dashboard.js
import React, { useState } from 'react';
import { useMarket } from '../../contexts/MarketContext';
import { useAuth } from '../../contexts/AuthContext';
import CoinCard from '../market/CoinCard';
import QuickStats from './QuickStats';
import PriceTicker from './PriceTicker';

const Dashboard = () => {
  const { coins, realtimePrices } = useMarket();
  const { isAuthenticated, user } = useAuth();
  const [sortBy, setSortBy] = useState('volume');
  const [searchTerm, setSearchTerm] = useState('');

  // 실시간으로 업데이트되는 코인 데이터
  const coinData = coins.map(coin => {
    const currentPrice = realtimePrices[coin.symbol] || parseFloat(coin.price) || 0;
    const change = parseFloat(coin.change) || 0;
    const volume = parseFloat(coin.volume) || 0;
    
    return {
      ...coin,
      currentPrice: currentPrice,
      change: change,
      volume: volume
    };
  }).filter(coin => 
    coin.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    coin.symbol.toLowerCase().includes(searchTerm.toLowerCase())
  ).sort((a, b) => {
    switch (sortBy) {
      case 'price': 
        return b.currentPrice - a.currentPrice;
      case 'change': 
        return Math.abs(b.change) - Math.abs(a.change);
      case 'volume': 
        return b.volume - a.volume;
      default: 
        return 0;
    }
  });

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">
            {isAuthenticated ? `${user?.username}님, 환영합니다!` : 'BeenCoin 모의투자'}
          </h1>
          <p className="text-gray-400">실시간 암호화폐 시장 현황 - 모의투자로 안전하게 연습하세요</p>
        </div>
        {isAuthenticated && <QuickStats />}
      </div>

      {/* 실시간 티커 */}
      {coinData.length > 0 && <PriceTicker coins={coinData.slice(0, 5)} />}

      {/* 검색 및 정렬 */}
      <div className="flex gap-4">
        <input
          type="text"
          placeholder="코인 검색..."
          className="flex-1 p-3 bg-gray-800 rounded-lg border border-gray-700 focus:outline-none focus:border-accent"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        <select 
          className="p-3 bg-gray-800 rounded-lg border border-gray-700 focus:outline-none focus:border-accent"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
        >
          <option value="volume">거래량 순</option>
          <option value="price">가격 순</option>
          <option value="change">변동률 순</option>
        </select>
      </div>

      {/* 코인 그리드 */}
      {coinData.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {coinData.map((coin) => (
            <CoinCard key={coin.symbol} coin={coin} />
          ))}
        </div>
      ) : (
        <div className="text-center py-20">
          <p className="text-gray-400">코인 데이터를 불러오는 중...</p>
        </div>
      )}

      {/* 비로그인 사용자용 CTA */}
      {!isAuthenticated && (
        <div className="text-center p-8 bg-gradient-to-r from-purple-900 to-blue-900 rounded-lg">
          <h2 className="text-2xl font-bold mb-4">지금 가입하고 100만원으로 모의투자 시작하기</h2>
          <p className="text-gray-300 mb-4">실시간 차트 분석, 다양한 코인 거래, 포트폴리오 관리까지</p>
          <p className="text-sm text-teal-300 mb-6">⚠️ 모의투자 플랫폼입니다. 실제 돈이 거래되지 않습니다.</p>
          <div className="space-x-4">
            <a href="/register" className="inline-block px-6 py-3 bg-accent text-white rounded-lg hover:bg-teal-600">
              무료로 시작하기
            </a>
            <a href="/login" className="inline-block px-6 py-3 border border-accent text-accent rounded-lg hover:bg-accent hover:text-white">
              로그인
            </a>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;