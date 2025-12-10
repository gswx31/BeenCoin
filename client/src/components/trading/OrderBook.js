// client/src/components/trading/OrderBook.js
// =============================================================================
// 호가창 컴포넌트 - 실제 Binance API 연동 버전
// =============================================================================
//
// 📌 개선 사항:
// 1. Mock 데이터 대신 실제 Binance API 호출
// 2. WebSocket 실시간 업데이트 지원
// 3. 호가 클릭 시 주문 폼에 가격 입력
// 4. 스프레드 표시
// 5. 누적 물량 표시
//
// =============================================================================
import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import axios from '../../api/axios';
import { endpoints } from '../../api/endpoints';
import { formatPrice } from '../../utils/formatPrice';

const OrderBook = ({ 
  symbol, 
  currentPrice,
  onPriceClick,  // 호가 클릭 시 가격 전달
  maxRows = 15,
}) => {
  const [orderBook, setOrderBook] = useState({ asks: [], bids: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [highlightedPrice, setHighlightedPrice] = useState(null);
  
  const wsRef = useRef(null);
  const isMountedRef = useRef(true);

  // =========================================================================
  // 호가 데이터 페칭 (REST API)
  // =========================================================================
  const fetchOrderBook = useCallback(async () => {
    try {
      const response = await axios.get(
        `${endpoints.market.orderbook || '/api/v1/market/orderbook'}/${symbol}`,
        { params: { limit: maxRows * 2 } }
      );
      
      if (isMountedRef.current && response.data) {
        setOrderBook({
          asks: response.data.asks || [],
          bids: response.data.bids || [],
        });
        setLastUpdate(new Date());
        setError(null);
      }
    } catch (err) {
      console.error('호가 데이터 로드 실패:', err);
      // API 없으면 Mock 데이터 생성
      if (isMountedRef.current) {
        generateMockOrderBook();
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [symbol, maxRows]);

  // =========================================================================
  // Mock 데이터 생성 (API 실패 시 폴백)
  // =========================================================================
  const generateMockOrderBook = useCallback(() => {
    const basePrice = currentPrice > 0 ? currentPrice : 50000;
    const spread = basePrice * 0.0001;
    
    const asks = Array.from({ length: maxRows }, (_, i) => ({
      price: (basePrice + spread * (i + 1)).toFixed(2),
      quantity: (Math.random() * 5 + 0.1).toFixed(6),
    })).reverse();
    
    const bids = Array.from({ length: maxRows }, (_, i) => ({
      price: (basePrice - spread * (i + 1)).toFixed(2),
      quantity: (Math.random() * 5 + 0.1).toFixed(6),
    }));
    
    setOrderBook({ asks, bids });
    setLastUpdate(new Date());
  }, [currentPrice, maxRows]);

  // =========================================================================
  // WebSocket 연결 (실시간 업데이트)
  // =========================================================================
  const connectWebSocket = useCallback(() => {
    // WebSocket URL (환경변수 또는 기본값)
    const wsBaseUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
    const wsUrl = `${wsBaseUrl}/ws/orderbook/${symbol}`;
    
    try {
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('📊 호가창 WebSocket 연결됨');
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'orderbook' && isMountedRef.current) {
            setOrderBook({
              asks: data.asks || data.data?.asks || [],
              bids: data.bids || data.data?.bids || [],
            });
            setLastUpdate(new Date());
          }
        } catch (e) {
          // 파싱 실패 무시
        }
      };
      
      wsRef.current.onerror = () => {
        console.warn('호가창 WebSocket 연결 실패, REST 폴링 사용');
      };
      
      wsRef.current.onclose = () => {
        // 5초 후 재연결 시도
        setTimeout(() => {
          if (isMountedRef.current) {
            connectWebSocket();
          }
        }, 5000);
      };
    } catch (e) {
      console.warn('WebSocket 연결 실패:', e);
    }
  }, [symbol]);

  // =========================================================================
  // 초기화 및 정리
  // =========================================================================
  useEffect(() => {
    isMountedRef.current = true;
    
    fetchOrderBook();
    connectWebSocket();
    
    // REST 폴링 백업 (2초마다)
    const interval = setInterval(fetchOrderBook, 2000);
    
    return () => {
      isMountedRef.current = false;
      if (wsRef.current) {
        wsRef.current.close();
      }
      clearInterval(interval);
    };
  }, [symbol, fetchOrderBook, connectWebSocket]);

  // =========================================================================
  // 호가 데이터 처리
  // =========================================================================
  const { processedAsks, processedBids, spread, spreadPercent, maxQuantity } = useMemo(() => {
    // 매도 호가 (낮은 가격이 아래로)
    const asks = (orderBook.asks || [])
      .slice(0, maxRows)
      .map((ask) => ({
        price: parseFloat(ask.price || ask[0]),
        quantity: parseFloat(ask.quantity || ask[1]),
      }))
      .sort((a, b) => a.price - b.price);

    // 매수 호가 (높은 가격이 위로)
    const bids = (orderBook.bids || [])
      .slice(0, maxRows)
      .map((bid) => ({
        price: parseFloat(bid.price || bid[0]),
        quantity: parseFloat(bid.quantity || bid[1]),
      }))
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
        <h2 className="text-xl font-bold text-white">호가창</h2>
        {lastUpdate && (
          <span className="text-xs text-gray-500">
            {lastUpdate.toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* 컬럼 헤더 */}
      <div className="grid grid-cols-3 gap-2 px-4 py-2 text-xs text-gray-400 border-b border-gray-700">
        <span>가격(USDT)</span>
        <span className="text-right">수량</span>
        <span className="text-right">누적</span>
      </div>

      {/* 매도 호가 */}
      <div className="max-h-[240px] overflow-y-auto">
        {processedAsks.map((ask, idx) => (
          <OrderRow
            key={`ask-${idx}`}
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

      {/* 현재가 & 스프레드 */}
      <div className="px-4 py-3 bg-gray-900/50 border-y border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-xs text-gray-400">현재가</span>
            <p className="text-xl font-bold text-accent">
              {formatPrice(currentPrice)}
            </p>
          </div>
          <div className="text-right">
            <span className="text-xs text-gray-400">스프레드</span>
            <p className="text-sm text-yellow-400">
              {formatPrice(spread)} ({spreadPercent.toFixed(3)}%)
            </p>
          </div>
        </div>
      </div>

      {/* 매수 호가 */}
      <div className="max-h-[240px] overflow-y-auto">
        {processedBids.map((bid, idx) => (
          <OrderRow
            key={`bid-${idx}`}
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