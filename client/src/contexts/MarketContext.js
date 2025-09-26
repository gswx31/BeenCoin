// client/src/contexts/MarketContext.js
import React, { createContext, useContext, useState, useEffect } from 'react';
import { toast } from 'react-toastify';

const MarketContext = createContext();

export const useMarket = () => {
  const context = useContext(MarketContext);
  if (!context) {
    throw new Error('useMarket must be used within a MarketProvider');
  }
  return context;
};

export const MarketProvider = ({ children }) => {
  const [coins, setCoins] = useState([]);
  const [realtimePrices, setRealtimePrices] = useState({});
  const [selectedCoin, setSelectedCoin] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // 코인 기본 정보 로드
    fetchCoinData();
    // 웹소켓 연결
    connectWebSocket();
  }, []);

  const fetchCoinData = async () => {
    try {
      const response = await fetch('/api/v1/market/coins');
      const coinData = await response.json();
      setCoins(coinData);
    } catch (error) {
      toast.error('코인 데이터 로딩 실패');
    }
  };

  const connectWebSocket = () => {
    const ws = new WebSocket('ws://localhost:8000/ws/realtime');
    
    ws.onopen = () => {
      setIsConnected(true);
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'price_update') {
        setRealtimePrices(prev => ({
          ...prev,
          ...data.data
        }));
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      // 재연결 시도
      setTimeout(connectWebSocket, 5000);
    };

    return () => ws.close();
  };

  const value = {
    coins,
    realtimePrices,
    selectedCoin,
    setSelectedCoin,
    isConnected
  };

  return (
    <MarketContext.Provider value={value}>
      {children}
    </MarketContext.Provider>
  );
};