// client/src/components/common/FavoriteCoins.js
// =============================================================================
// 즐겨찾기 코인 컴포넌트
// =============================================================================
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMarket } from '../../contexts/MarketContext';
import { formatPrice } from '../../utils/formatPrice';

const STORAGE_KEY = 'beencoin_favorites';

const FavoriteCoins = ({ onSelectCoin }) => {
  const navigate = useNavigate();
  const { coins, realtimePrices } = useMarket();
  const [favorites, setFavorites] = useState([]);

  // =========================================================================
  // localStorage에서 즐겨찾기 로드
  // =========================================================================
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        setFavorites(JSON.parse(saved));
      }
    } catch (e) {
      console.error('즐겨찾기 로드 실패:', e);
    }
  }, []);

  // =========================================================================
  // 즐겨찾기 저장
  // =========================================================================
  const saveFavorites = useCallback((newFavorites) => {
    setFavorites(newFavorites);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newFavorites));
    } catch (e) {
      console.error('즐겨찾기 저장 실패:', e);
    }
  }, []);

  // =========================================================================
  // 즐겨찾기 토글
  // =========================================================================
  const toggleFavorite = useCallback((symbol) => {
    setFavorites(prev => {
      const newFavorites = prev.includes(symbol)
        ? prev.filter(s => s !== symbol)
        : [...prev, symbol];
      
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newFavorites));
      return newFavorites;
    });
  }, []);

  // =========================================================================
  // 즐겨찾기 여부 확인
  // =========================================================================
  const isFavorite = useCallback((symbol) => {
    return favorites.includes(symbol);
  }, [favorites]);

  // =========================================================================
  // 코인 클릭 핸들러
  // =========================================================================
  const handleCoinClick = (symbol) => {
    if (onSelectCoin) {
      onSelectCoin(symbol);
    } else {
      navigate(`/trade/${symbol}`);
    }
  };

  // =========================================================================
  // 즐겨찾기 코인 데이터
  // =========================================================================
  const favoriteCoinsData = favorites
    .map(symbol => {
      const coin = coins.find(c => c.symbol === symbol);
      const price = realtimePrices[symbol] || coin?.price || 0;
      const change = coin?.priceChangePercent || 0;
      
      return {
        symbol,
        price,
        change: parseFloat(change),
        name: coin?.name || symbol.replace('USDT', ''),
      };
    })
    .filter(c => c.price > 0);

  // =========================================================================
  // 렌더링
  // =========================================================================
  if (favorites.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-white mb-3">⭐ 즐겨찾기</h3>
        <p className="text-gray-400 text-sm text-center py-4">
          즐겨찾기한 코인이 없습니다.<br/>
          코인 목록에서 ⭐를 클릭해 추가하세요.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-lg font-semibold text-white mb-3">⭐ 즐겨찾기</h3>
      
      <div className="space-y-2">
        {favoriteCoinsData.map(coin => (
          <div 
            key={coin.symbol}
            className="flex items-center justify-between p-2 rounded bg-gray-700/50 hover:bg-gray-700 cursor-pointer transition-colors"
            onClick={() => handleCoinClick(coin.symbol)}
          >
            <div className="flex items-center gap-3">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggleFavorite(coin.symbol);
                }}
                className="text-yellow-400 hover:text-yellow-300"
              >
                ⭐
              </button>
              <div>
                <span className="font-semibold text-white">{coin.name}</span>
                <span className="text-gray-400 text-xs ml-1">/ USDT</span>
              </div>
            </div>
            
            <div className="text-right">
              <p className="text-white font-mono">{formatPrice(coin.price)}</p>
              <p className={`text-xs ${coin.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {coin.change >= 0 ? '+' : ''}{coin.change.toFixed(2)}%
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// =========================================================================
// 즐겨찾기 버튼 (개별 사용)
// =========================================================================
export const FavoriteButton = ({ symbol, size = 'md' }) => {
  const [isFav, setIsFav] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const favorites = JSON.parse(saved);
        setIsFav(favorites.includes(symbol));
      }
    } catch (e) {}
  }, [symbol]);

  const toggle = (e) => {
    e.stopPropagation();
    
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      let favorites = saved ? JSON.parse(saved) : [];
      
      if (favorites.includes(symbol)) {
        favorites = favorites.filter(s => s !== symbol);
      } else {
        favorites.push(symbol);
      }
      
      localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites));
      setIsFav(favorites.includes(symbol));
    } catch (e) {}
  };

  const sizeClass = size === 'sm' ? 'text-sm' : size === 'lg' ? 'text-xl' : 'text-base';

  return (
    <button
      onClick={toggle}
      className={`${sizeClass} transition-colors ${
        isFav ? 'text-yellow-400' : 'text-gray-500 hover:text-yellow-400'
      }`}
      title={isFav ? '즐겨찾기 해제' : '즐겨찾기 추가'}
    >
      {isFav ? '⭐' : '☆'}
    </button>
  );
};

export default FavoriteCoins;