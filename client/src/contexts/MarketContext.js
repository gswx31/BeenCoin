// client/src/contexts/MarketContext.js
// =============================================================================
// 마켓 데이터 Context - WebSocket 안정성 강화
// =============================================================================
import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import axios from '../api/axios';
import { endpoints, getWebSocketUrl } from '../api/endpoints';
import { toast } from 'react-toastify';

const MarketContext = createContext(null);

export const useMarket = () => {
  const context = useContext(MarketContext);
  if (!context) {
    throw new Error('useMarket must be used within a MarketProvider');
  }
  return context;
};

// =============================================================================
// MarketProvider 컴포넌트
// =============================================================================
export const MarketProvider = ({ children }) => {
  const [coins, setCoins] = useState([]);
  const [realtimePrices, setRealtimePrices] = useState({});
  const [selectedCoin, setSelectedCoin] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // WebSocket 참조
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  // ===========================================
  // 초기 데이터 로드
  // ===========================================
  useEffect(() => {
    fetchCoinData();
    connectWebSocket();

    // 클린업
    return () => {
      disconnectWebSocket();
    };
  }, []);

  // 주기적 데이터 갱신 (WebSocket 백업)
  useEffect(() => {
    const interval = setInterval(() => {
      if (!isConnected) {
        fetchCoinData();
      }
    }, 30000); // 30초마다

    return () => clearInterval(interval);
  }, [isConnected]);

  // ===========================================
  // 코인 데이터 조회 (REST API)
  // ===========================================
  const fetchCoinData = useCallback(async () => {
    try {
      setError(null);
      const response = await axios.get(endpoints.market.coins);

      const coinData = response.data;
      console.log('📊 Fetched coin data:', coinData.length, 'coins');

      setCoins(coinData);

      // 초기 가격 설정
      const initialPrices = {};
      coinData.forEach((coin) => {
        if (coin.price) {
          initialPrices[coin.symbol] = parseFloat(coin.price);
        }
      });
      setRealtimePrices((prev) => ({ ...prev, ...initialPrices }));

      setLoading(false);
    } catch (error) {
      console.error('❌ Error fetching coin data:', error);
      setError('코인 데이터를 불러올 수 없습니다.');
      setLoading(false);

      // 5초 후 재시도
      setTimeout(fetchCoinData, 5000);
    }
  }, []);

  // ===========================================
  // WebSocket 연결
  // ===========================================
  const connectWebSocket = useCallback(() => {
    // 기존 연결 정리
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsUrl = getWebSocketUrl(endpoints.websocket.realtime);
    console.log('🔌 Connecting WebSocket:', wsUrl);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ WebSocket connected');
        setIsConnected(true);
        reconnectAttempts.current = 0;

        // 연결 성공 시 구독 메시지 전송 (필요한 경우)
        ws.send(JSON.stringify({ type: 'subscribe', channels: ['prices'] }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'price_update' && data.data) {
            // 가격 업데이트
            const parsedPrices = {};
            Object.entries(data.data).forEach(([symbol, price]) => {
              const numPrice = parseFloat(price);
              if (!isNaN(numPrice) && numPrice > 0) {
                parsedPrices[symbol] = numPrice;
              }
            });

            setRealtimePrices((prev) => ({
              ...prev,
              ...parsedPrices,
            }));
          } else if (data.type === 'ping') {
            // Heartbeat 응답
            ws.send(JSON.stringify({ type: 'pong' }));
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        setIsConnected(false);
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;

        // 재연결 시도
        scheduleReconnect();
      };
    } catch (error) {
      console.error('❌ WebSocket connection error:', error);
      setIsConnected(false);
      scheduleReconnect();
    }
  }, []);

  // ===========================================
  // WebSocket 재연결
  // ===========================================
  const scheduleReconnect = useCallback(() => {
    if (reconnectAttempts.current >= maxReconnectAttempts) {
      console.warn('Max reconnect attempts reached');
      toast.warning('실시간 연결이 끊어졌습니다. 페이지를 새로고침해주세요.');
      return;
    }

    // 지수 백오프
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
    reconnectAttempts.current += 1;

    console.log(`🔄 Reconnecting in ${delay / 1000}s (attempt ${reconnectAttempts.current})`);

    reconnectTimeoutRef.current = setTimeout(() => {
      connectWebSocket();
    }, delay);
  }, [connectWebSocket]);

  // ===========================================
  // WebSocket 연결 해제
  // ===========================================
  const disconnectWebSocket = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Component unmount');
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  // ===========================================
  // 특정 코인 상세 조회
  // ===========================================
  const fetchCoinDetail = useCallback(async (symbol) => {
    try {
      const response = await axios.get(endpoints.market.coinDetail(symbol));
      return response.data;
    } catch (error) {
      console.error(`Error fetching ${symbol} detail:`, error);
      throw error;
    }
  }, []);

  // ===========================================
  // 히스토리컬 데이터 조회
  // ===========================================
  const fetchHistoricalData = useCallback(async (symbol, interval = '1h', limit = 24) => {
    try {
      const response = await axios.get(endpoints.market.historical(symbol), {
        params: { interval, limit },
      });
      return response.data;
    } catch (error) {
      console.error(`Error fetching ${symbol} historical data:`, error);
      throw error;
    }
  }, []);

  // ===========================================
  // 최근 체결 내역 조회
  // ===========================================
  const fetchRecentTrades = useCallback(async (symbol, limit = 20) => {
    try {
      const response = await axios.get(endpoints.market.trades(symbol), {
        params: { limit },
      });
      return response.data;
    } catch (error) {
      console.error(`Error fetching ${symbol} trades:`, error);
      throw error;
    }
  }, []);

  // ===========================================
  // 호가 데이터 조회
  // ===========================================
  const fetchOrderBook = useCallback(async (symbol, limit = 10) => {
    try {
      const response = await axios.get(endpoints.market.orderbook(symbol), {
        params: { limit },
      });
      return response.data;
    } catch (error) {
      console.error(`Error fetching ${symbol} orderbook:`, error);
      throw error;
    }
  }, []);

  // ===========================================
  // 가격 조회 헬퍼
  // ===========================================
  const getPrice = useCallback(
    (symbol) => {
      return realtimePrices[symbol] || null;
    },
    [realtimePrices]
  );

  // ===========================================
  // Context 값
  // ===========================================
  const value = {
    // 상태
    coins,
    realtimePrices,
    selectedCoin,
    setSelectedCoin,
    isConnected,
    loading,
    error,

    // 함수
    fetchCoinData,
    fetchCoinDetail,
    fetchHistoricalData,
    fetchRecentTrades,
    fetchOrderBook,
    getPrice,
    reconnect: connectWebSocket,
  };

  return <MarketContext.Provider value={value}>{children}</MarketContext.Provider>;
};

export default MarketContext;