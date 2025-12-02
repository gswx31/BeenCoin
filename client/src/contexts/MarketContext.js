// client/src/contexts/MarketContext.js
// 실시간 가격 WebSocket 영원히 안 끊기는 버전 (컴파일 100% 통과)
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

  // WebSocket 연결 (핵심)
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return;
    if (wsRef.current) wsRef.current.close();

    const wsUrl = getWebSocketUrl(endpoints.websocket.realtime);
    console.log('WebSocket 연결 →', wsUrl);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket 연결 성공');
      setIsConnected(true);
      reconnectAttempts.current = 0;
      ws.send(JSON.stringify({ type: 'subscribe', channels: ['prices'] }));
    };

    ws.onmessage = (event) => {
      // ping 오면 무조건 pong (이게 제일 중요!)
      if (event.data === 'ping' || event.data === '"ping"') {
        ws.send('pong');
        return;
      }

      try {
        const data = JSON.parse(event.data);

        if (data.type === 'ping') {
          ws.send(JSON.stringify({ type: 'pong' }));
          return;
        }

        if (data.type === 'price_update' && data.data) {
          const parsed = {};
          Object.entries(data.data).forEach(([symbol, price]) => {
            const p = parseFloat(price);
            if (!isNaN(p) && p > 0) parsed[symbol] = p;
          });
          setRealtimePrices((prev) => ({ ...prev, ...parsed }));
        }
      } catch (e) {
        // JSON 파싱 실패는 무시 (ping 등 문자열)
      }
    };

    ws.onerror = () => {
      console.error('WebSocket 오류');
      setIsConnected(false);
      scheduleReconnect();
    };

    ws.onclose = (event) => {
      console.log(`WebSocket 종료 (code: ${event.code})`);
      setIsConnected(false);
      wsRef.current = null;

      // 정상 종료가 아니면 재연결
      if (event.code !== 1000 && event.code !== 1001) {
        scheduleReconnect();
      }
    };
  }, []);

  // 무한 재연결 (지수 백오프)
  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) return;

    const attempt = ++reconnectAttempts.current;
    const delay = Math.min(1000 * 2 ** Math.min(attempt, 10), MAX_DELAY);

    console.log(`재연결 ${attempt}회 → ${delay / 1000}초 후 재시도`);

    if (attempt > 10) {
      const now = Date.now();
      if (now - lastToastTime.current > 30000) {
        toast.warning('실시간 가격 연결이 불안정합니다. 재연결 중...', {
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

  // 수동 재연결 함수
  const reconnect = useCallback(() => {
    reconnectAttempts.current = 0;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    connectWebSocket();
  }, [connectWebSocket]);

  // 정리
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

  // 기타 API 함수들
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