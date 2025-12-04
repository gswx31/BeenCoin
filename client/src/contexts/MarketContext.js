// client/src/contexts/MarketContext.js
// =============================================================================
// 마켓 데이터 Context - 실시간 가격 WebSocket
// =============================================================================
import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
} from 'react';
import axios from '../api/axios';
import { endpoints, getWebSocketUrl } from '../api/endpoints';
import { toast } from 'react-toastify';

const MarketContext = createContext(null);

export const useMarket = () => {
  const context = useContext(MarketContext);
  if (!context) throw new Error('useMarket must be used within a MarketProvider');
  return context;
};

export const MarketProvider = ({ children }) => {
  const [coins, setCoins] = useState([]);
  const [realtimePrices, setRealtimePrices] = useState({});
  const [selectedCoin, setSelectedCoin] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const lastToastTime = useRef(0);

  const MAX_DELAY = 30000;

  // 초기 데이터 + WebSocket 연결
  useEffect(() => {
    fetchCoinData();
    connectWebSocket();

    return () => {
      disconnectWebSocket();
    };
  }, []);

  // WebSocket 끊기면 30초마다 REST 폴링 백업
  useEffect(() => {
    const interval = setInterval(() => {
      if (!isConnected) fetchCoinData();
    }, 30000);
    return () => clearInterval(interval);
  }, [isConnected]);

  // REST 코인 데이터 로드
  const fetchCoinData = useCallback(async () => {
    try {
      setError(null);
      const { data } = await axios.get(endpoints.market.coins);

      setCoins(data);

      const initialPrices = {};
      data.forEach((coin) => {
        if (coin.price) initialPrices[coin.symbol] = parseFloat(coin.price);
      });
      setRealtimePrices((prev) => ({ ...prev, ...initialPrices }));

      setLoading(false);
    } catch (err) {
      console.error('코인 데이터 로드 실패:', err);
      setError('코인 데이터를 불러올 수 없습니다.');
      setLoading(false);
      setTimeout(fetchCoinData, 5000);
    }
  }, []);

  // WebSocket 연결
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return;
    if (wsRef.current) wsRef.current.close();

    const wsUrl = getWebSocketUrl(endpoints.websocket.realtime);
    console.log('WebSocket 연결 →', wsUrl);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('✅ WebSocket 연결 성공');
      setIsConnected(true);
      reconnectAttempts.current = 0;
      ws.send(JSON.stringify({ type: 'subscribe', channels: ['prices'] }));
    };

    ws.onmessage = (event) => {
      // ping 응답
      if (event.data === 'ping') {
        ws.send('pong');
        return;
      }

      try {
        const message = JSON.parse(event.data);

        if (message.type === 'ping') {
          ws.send(JSON.stringify({ type: 'pong' }));
          return;
        }

        if (message.type === 'prices' && message.data) {
          setRealtimePrices((prev) => ({ ...prev, ...message.data }));
        }

        if (message.type === 'price_update' && message.symbol && message.price) {
          setRealtimePrices((prev) => ({
            ...prev,
            [message.symbol]: parseFloat(message.price),
          }));
        }
      } catch (e) {
        // JSON 파싱 실패 무시
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket 오류:', error);
      setIsConnected(false);
    };

    ws.onclose = (event) => {
      console.log('WebSocket 닫힘:', event.code, event.reason);
      setIsConnected(false);
      wsRef.current = null;
      scheduleReconnect();
    };
  }, []);

  // 재연결 스케줄링
  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) return;

    reconnectAttempts.current += 1;
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current - 1), MAX_DELAY);

    console.log(`🔄 ${delay / 1000}초 후 재연결 시도 (#${reconnectAttempts.current})`);

    if (reconnectAttempts.current === 3) {
      const now = Date.now();
      if (now - lastToastTime.current > 60000) {
        toast.warning('실시간 연결이 불안정합니다. 재연결 중...', {
          toastId: 'ws-unstable',
        });
        lastToastTime.current = now;
      }
    }

    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectTimeoutRef.current = null;
      connectWebSocket();
    }, delay);
  }, [connectWebSocket]);

  // 수동 재연결
  const reconnect = useCallback(() => {
    reconnectAttempts.current = 0;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    connectWebSocket();
  }, [connectWebSocket]);

  // WebSocket 정리
  const disconnectWebSocket = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close(1000, 'Unmount');
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // API 함수들
  const fetchCoinDetail = async (symbol) => {
    const { data } = await axios.get(endpoints.market.coinDetail(symbol));
    return data;
  };

  const fetchHistoricalData = async (symbol, interval = '1h', limit = 24) => {
    const { data } = await axios.get(endpoints.market.historical(symbol), {
      params: { interval, limit },
    });
    return data;
  };

  const fetchRecentTrades = async (symbol, limit = 20) => {
    const { data } = await axios.get(endpoints.market.trades(symbol), { params: { limit } });
    return data;
  };

  const fetchOrderBook = async (symbol, limit = 10) => {
    const { data } = await axios.get(endpoints.market.orderbook(symbol), { params: { limit } });
    return data;
  };

  const getPrice = useCallback((symbol) => realtimePrices[symbol] ?? null, [realtimePrices]);

  const value = {
    coins,
    realtimePrices,
    selectedCoin,
    setSelectedCoin,
    isConnected,
    loading,
    error,
    fetchCoinData,
    fetchCoinDetail,
    fetchHistoricalData,
    fetchRecentTrades,
    fetchOrderBook,
    getPrice,
    reconnect,
  };

  return <MarketContext.Provider value={value}>{children}</MarketContext.Provider>;
};

export default MarketContext;