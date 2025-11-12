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
    fetchCoinData();
    connectWebSocket();
  }, []);

  const fetchCoinData = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/market/coins');
      
      if (!response.ok) {
        throw new Error('Failed to fetch coin data');
      }
      
      const coinData = await response.json();
      console.log('Fetched coin data:', coinData);
      setCoins(coinData);
      
      // 초기 가격 설정
      const initialPrices = {};
      coinData.forEach(coin => {
        if (coin.price) {
          initialPrices[coin.symbol] = parseFloat(coin.price);
        }
      });
      setRealtimePrices(initialPrices);
    } catch (error) {
      console.error('Error fetching coin data:', error);
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
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'price_update' && data.data) {
          // 문자열을 숫자로 변환
          const parsedPrices = {};
          Object.keys(data.data).forEach(symbol => {
            parsedPrices[symbol] = parseFloat(data.data[symbol]);
          });
          
          setRealtimePrices(prev => ({
            ...prev,
            ...parsedPrices
          }));
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log('WebSocket disconnected, reconnecting in 5s...');
      // 재연결 시도
      setTimeout(connectWebSocket, 5000);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
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