// client/src/components/trading/OrderBook.js
// =============================================================================
// 호가창 컴포넌트 - 안정성 개선 버전
// =============================================================================
//
// 📌 개선 사항:
// 1. WebSocket과 REST 폴링 경쟁 조건 해결
// 2. 데이터 정규화 강화 (배열/객체 형식 통합)
// 3. WebSocket 재연결 로직 개선
// 4. 메모리 누수 방지
//
// =============================================================================
import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import axios from '../../api/axios';
import { endpoints } from '../../api/endpoints';
import { formatPrice } from '../../utils/formatPrice';

const OrderBook = ({ 
  symbol, 
  currentPrice,
  onPriceClick,
  maxRows = 15,
}) => {
  const [orderBook, setOrderBook] = useState({ asks: [], bids: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [highlightedPrice, setHighlightedPrice] = useState(null);
  // 📌 추가: WebSocket 연결 상태 추적
  const [isWsConnected, setIsWsConnected] = useState(false);
  
  const wsRef = useRef(null);
  const isMountedRef = useRef(true);
  // 📌 추가: 재연결 관리
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const pollingIntervalRef = useRef(null);
  const maxReconnectAttempts = 5;

  // =========================================================================
  // 📌 개선: 데이터 정규화 함수 추가
  // =========================================================================
  const normalizeOrderBookData = useCallback((data) => {
    if (!data) return { asks: [], bids: [] };

    const normalizeEntry = (entry) => {
      if (Array.isArray(entry)) {
        // 배열 형식: [price, quantity]
        return {
          price: parseFloat(entry[0]) || 0,
          quantity: parseFloat(entry[1]) || 0,
        };
      } else if (typeof entry === 'object') {
        // 객체 형식: {price, quantity} or {price, qty}
        return {
          price: parseFloat(entry.price || entry[0]) || 0,
          quantity: parseFloat(entry.quantity || entry.qty || entry[1]) || 0,
        };
      }
      return { price: 0, quantity: 0 };
    };

    const asks = (data.asks || [])
      .map(normalizeEntry)
      .filter(item => item.price > 0 && item.quantity > 0);
    
    const bids = (data.bids || [])
      .map(normalizeEntry)
      .filter(item => item.price > 0 && item.quantity > 0);

    return { asks, bids };
  }, []);

  // =========================================================================
  // 📌 개선: REST API 호가 데이터 페칭 (경쟁 조건 방지)
  // =========================================================================
  const fetchOrderBook = useCallback(async () => {
    // WebSocket이 연결되어 있으면 REST 폴링 스킵
    if (isWsConnected) {
      return;
    }

    try {
      const response = await axios.get(
        `${endpoints.market.orderbook}/${symbol}`,
        { params: { limit: maxRows * 2 }, timeout: 5000 }
      );
      
      if (isMountedRef.current && response.data) {
        const normalized = normalizeOrderBookData(response.data);
        setOrderBook(normalized);
        setLastUpdate(new Date());
        setError(null);
      }
    } catch (err) {
      console.error('호가 데이터 로드 실패:', err);
      if (isMountedRef.current) {
        generateMockOrderBook();
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [symbol, maxRows, isWsConnected, normalizeOrderBookData]);

  // =========================================================================
  // Mock 데이터 생성 (API 실패 시 폴백)
  // =========================================================================
  const generateMockOrderBook = useCallback(() => {
    const basePrice = currentPrice > 0 ? currentPrice : 50000;
    const spread = basePrice * 0.0001;
    
    const asks = Array.from({ length: maxRows }, (_, i) => ({
      price: basePrice + spread * (i + 1),
      quantity: Math.random() * 5 + 0.1,
    })).reverse();
    
    const bids = Array.from({ length: maxRows }, (_, i) => ({
      price: basePrice - spread * (i + 1),
      quantity: Math.random() * 5 + 0.1,
    }));
    
    setOrderBook({ asks, bids });
    setLastUpdate(new Date());
    setError('Mock 데이터 사용 중');
  }, [currentPrice, maxRows]);

  // =========================================================================
  // 📌 개선: WebSocket 연결 관리 (재연결 로직 강화)
  // =========================================================================
  const connectWebSocket = useCallback(() => {
    // 최대 재연결 시도 횟수 초과시 중단
    if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
      console.warn('최대 재연결 시도 횟수 초과, REST 폴링으로 전환');
      setIsWsConnected(false);
      return;
    }

    const wsBaseUrl = process.env.REACT_APP_WS_URL || 
      (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + 
      '//' + window.location.host;
    const wsUrl = `${wsBaseUrl}/ws/orderbook/${symbol}`;
    
    try {
      // 기존 WebSocket 정리
      if (wsRef.current) {
        wsRef.current.close();
      }

      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('📊 호가창 WebSocket 연결됨');
        setIsWsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0; // 재연결 카운터 리셋
      };
      
      wsRef.current.onmessage = (event) => {
        if (!isMountedRef.current) return;

        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'orderbook') {
            const bookData = data.data || data;
            const normalized = normalizeOrderBookData(bookData);
            
            setOrderBook(normalized);
            setLastUpdate(new Date());
            setError(null);
          }
        } catch (e) {
          console.warn('WebSocket 메시지 파싱 실패:', e);
        }
      };
      
      wsRef.current.onerror = (error) => {
        console.warn('호가창 WebSocket 오류:', error);
        setIsWsConnected(false);
      };
      
      wsRef.current.onclose = () => {
        setIsWsConnected(false);
        
        // 재연결 시도 (지수 백오프)
        if (isMountedRef.current && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          
          console.log(`WebSocket 재연결 시도 ${reconnectAttemptsRef.current}/${maxReconnectAttempts} (${delay}ms 후)`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            if (isMountedRef.current) {
              connectWebSocket();
            }
          }, delay);
        }
      };
    } catch (e) {
      console.warn('WebSocket 연결 실패:', e);
      setIsWsConnected(false);
    }
  }, [symbol, normalizeOrderBookData]);

  // =========================================================================
  // 📌 개선: 초기화 및 정리 (메모리 누수 방지)
  // =========================================================================
  useEffect(() => {
    isMountedRef.current = true;
    reconnectAttemptsRef.current = 0;
    
    // 초기 데이터 로드
    fetchOrderBook();
    
    // WebSocket 연결 시도
    connectWebSocket();
    
    // REST 폴링 백업 (WebSocket이 연결되지 않았을 때만)
    pollingIntervalRef.current = setInterval(() => {
      if (!isWsConnected) {
        fetchOrderBook();
      }
    }, 3000);
    
    return () => {
      isMountedRef.current = false;
      
      // WebSocket 정리
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      
      // 타이머 정리
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [symbol, fetchOrderBook, connectWebSocket, isWsConnected]);

  // =========================================================================
  // 호가 데이터 처리
  // =========================================================================
  const { processedAsks, processedBids, spread, spreadPercent, maxQuantity } = useMemo(() => {
    // 매도 호가 (낮은 가격이 아래로)
    const asks = orderBook.asks
      .slice(0, maxRows)
      .sort((a, b) => a.price - b.price);

    // 매수 호가 (높은 가격이 위로)
    const bids = orderBook.bids
      .slice(0, maxRows)
      .sort((a, b) => b.price - a.price);

    // 누적 물량 계산
    let askTotal = 0;
    asks.forEach(ask => {
      askTotal += ask.quantity;
      ask.total = askTotal;
    });

    let bidTotal = 0;
    bids.forEach(bid => {
      bidTotal += bid.quantity;
      bid.total = bidTotal;
    });

    // 최대 물량 (바 차트용)
    const maxQty = Math.max(
      ...asks.map(a => a.quantity),
      ...bids.map(b => b.quantity),
      0.001
    );

    // 스프레드 계산
    const lowestAsk = asks.length > 0 ? asks[0].price : currentPrice;
    const highestBid = bids.length > 0 ? bids[0].price : currentPrice;
    const spreadVal = lowestAsk - highestBid;
    const spreadPct = highestBid > 0 ? (spreadVal / highestBid) * 100 : 0;

    return {
      processedAsks: asks.reverse(), // 높은 가격이 위로
      processedBids: bids,
      spread: spreadVal,
      spreadPercent: spreadPct,
      maxQuantity: maxQty,
    };
  }, [orderBook, maxRows, currentPrice]);

  // =========================================================================
  // 호가 클릭 핸들러
  // =========================================================================
  const handlePriceClick = useCallback((price) => {
    setHighlightedPrice(price);
    setTimeout(() => setHighlightedPrice(null), 500);
    
    if (onPriceClick) {
      onPriceClick(price);
    }
  }, [onPriceClick]);

  // =========================================================================
  // 로딩 상태
  // =========================================================================
  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 animate-pulse">
        <div className="h-6 bg-gray-700 rounded mb-4 w-1/3"></div>
        <div className="space-y-2">
          {[...Array(10)].map((_, i) => (
            <div key={i} className="h-6 bg-gray-700/50 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  // =========================================================================
  // 렌더링
  // =========================================================================
  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden">
      {/* 헤더 */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <div className="flex items-center space-x-2">
          <h3 className="text-lg font-bold">호가창</h3>
          {/* 📌 추가: 연결 상태 표시 */}
          <div 
            className={`w-2 h-2 rounded-full ${isWsConnected ? 'bg-green-500' : 'bg-yellow-500'}`} 
            title={isWsConnected ? 'WebSocket 연결됨' : 'REST API 사용 중'}
          />
        </div>
        {lastUpdate && (
          <span className="text-xs text-gray-400">
            {lastUpdate.toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* 에러 표시 */}
      {error && (
        <div className="px-4 py-2 bg-yellow-900/20 border-b border-yellow-700">
          <p className="text-xs text-yellow-400">{error}</p>
        </div>
      )}

      {/* 컬럼 헤더 */}
      <div className="grid grid-cols-3 gap-2 px-4 py-2 bg-gray-700/30 text-xs text-gray-400 font-semibold">
        <span>가격(USDT)</span>
        <span className="text-right">수량</span>
        <span className="text-right">누적</span>
      </div>

      {/* 매도 호가 */}
      <div className="max-h-[240px] overflow-y-auto">
        {processedAsks.map((ask, idx) => (
          <OrderRow
            key={`ask-${idx}-${ask.price}`}
            type="ask"
            price={ask.price}
            quantity={ask.quantity}
            total={ask.total}
            maxQuantity={maxQuantity}
            isHighlighted={highlightedPrice === ask.price}
            onClick={() => handlePriceClick(ask.price)}
          />
        ))}
      </div>

      {/* 스프레드 */}
      <div className="px-4 py-2 bg-gray-700/50">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-400">스프레드</span>
          <div className="text-right">
            <p className="font-mono text-white">${spread.toFixed(2)}</p>
            <p className="text-gray-400 text-xs">
              ({spreadPercent.toFixed(3)}%)
            </p>
          </div>
        </div>
      </div>

      {/* 매수 호가 */}
      <div className="max-h-[240px] overflow-y-auto">
        {processedBids.map((bid, idx) => (
          <OrderRow
            key={`bid-${idx}-${bid.price}`}
            type="bid"
            price={bid.price}
            quantity={bid.quantity}
            total={bid.total}
            maxQuantity={maxQuantity}
            isHighlighted={highlightedPrice === bid.price}
            onClick={() => handlePriceClick(bid.price)}
          />
        ))}
      </div>

      {/* 합계 */}
      <div className="px-4 py-3 border-t border-gray-700 text-xs">
        <div className="flex justify-between text-gray-400">
          <span>총 매도: <span className="text-red-400">{processedAsks.reduce((s, a) => s + a.quantity, 0).toFixed(4)}</span></span>
          <span>총 매수: <span className="text-green-400">{processedBids.reduce((s, b) => s + b.quantity, 0).toFixed(4)}</span></span>
        </div>
      </div>
    </div>
  );
};

// =============================================================================
// 개별 호가 행 컴포넌트
// =============================================================================
const OrderRow = ({ type, price, quantity, total, maxQuantity, isHighlighted, onClick }) => {
  const isAsk = type === 'ask';
  const barWidth = Math.min((quantity / maxQuantity) * 100, 100);
  
  return (
    <div 
      className={`relative grid grid-cols-3 gap-2 px-4 py-1.5 cursor-pointer transition-all duration-150
        ${isHighlighted 
          ? (isAsk ? 'bg-red-500/30 scale-[1.02]' : 'bg-green-500/30 scale-[1.02]')
          : 'hover:bg-gray-700/50'
        }`}
      onClick={onClick}
    >
      {/* 배경 바 */}
      <div 
        className={`absolute inset-y-0 right-0 opacity-20 transition-all ${
          isAsk ? 'bg-red-500' : 'bg-green-500'
        }`}
        style={{ width: `${barWidth}%` }}
      />
      
      {/* 가격 */}
      <span className={`relative z-10 font-mono text-sm font-semibold ${
        isAsk ? 'text-red-400' : 'text-green-400'
      }`}>
        {formatPrice(price)}
      </span>
      
      {/* 수량 */}
      <span className="relative z-10 text-right text-sm text-gray-300 font-mono">
        {quantity.toFixed(4)}
      </span>
      
      {/* 누적 */}
      <span className="relative z-10 text-right text-sm text-gray-500 font-mono">
        {total.toFixed(4)}
      </span>
    </div>
  );
};

export default OrderBook;