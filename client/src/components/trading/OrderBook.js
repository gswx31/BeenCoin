// client/src/components/trading/OrderBook.js
// =============================================================================
// 호가창 컴포넌트 
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
  const [lastUpdate, setLastUpdate] = useState(null);
  const [highlightedPrice, setHighlightedPrice] = useState(null);
  
  const wsRef = useRef(null);
  const isMountedRef = useRef(true);
  const pollingIntervalRef = useRef(null);

  // 데이터 정규화 함수
  const normalizeOrderBookData = useCallback((data) => {
    if (!data) return { asks: [], bids: [] };

    const normalizeEntry = (entry) => {
      if (Array.isArray(entry)) {
        return {
          price: parseFloat(entry[0]) || 0,
          quantity: parseFloat(entry[1]) || 0,
        };
      } else if (typeof entry === 'object') {
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

  // REST API 호가 데이터 페칭
  const fetchOrderBook = useCallback(async () => {
    try {
      const response = await axios.get(
        `${endpoints.market.orderbook}/${symbol}`,
        { params: { limit: maxRows * 2 }, timeout: 3000 }
      );
      
      if (isMountedRef.current && response.data) {
        const normalized = normalizeOrderBookData(response.data);
        setOrderBook(normalized);
        setLastUpdate(new Date());
        setLoading(false);
      }
    } catch (err) {
      console.warn('호가 데이터 로드 실패, 재시도 중...', err);
      if (isMountedRef.current) {
        generateMockOrderBook();
      }
    }
  }, [symbol, maxRows, normalizeOrderBookData]);

  // Mock 데이터 생성 (테스트용)
  const generateMockOrderBook = useCallback(() => {
    const basePrice = currentPrice > 0 ? currentPrice : 50000;
    const spread = basePrice * 0.0001;
    
    const asks = Array.from({ length: maxRows }, (_, i) => ({
      price: basePrice + spread * (i + 1),
      quantity: Math.random() * 5 + 0.1,
    }));
    
    const bids = Array.from({ length: maxRows }, (_, i) => ({
      price: basePrice - spread * (i + 1),
      quantity: Math.random() * 5 + 0.1,
    }));
    
    setOrderBook({ asks, bids });
    setLastUpdate(new Date());
    setLoading(false);
  }, [currentPrice, maxRows]);

  // WebSocket 연결 (옵션)
  useEffect(() => {
    const wsBaseUrl = process.env.REACT_APP_WS_URL || 
      (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + 
      '//' + window.location.host;
    
    try {
      wsRef.current = new WebSocket(`${wsBaseUrl}/ws/orderbook/${symbol}`);
      
      wsRef.current.onmessage = (event) => {
        if (!isMountedRef.current) return;

        try {
          const data = JSON.parse(event.data);
          if (data.type === 'orderbook') {
            const bookData = data.data || data;
            const normalized = normalizeOrderBookData(bookData);
            setOrderBook(normalized);
            setLastUpdate(new Date());
          }
        } catch (e) {
          console.warn('WebSocket 메시지 파싱 실패:', e);
        }
      };
      
      wsRef.current.onerror = (error) => {
        console.warn('호가창 WebSocket 오류:', error);
      };
    } catch (e) {
      console.warn('WebSocket 연결 실패, REST API 사용:', e);
    }

    // REST 폴링
    fetchOrderBook();
    pollingIntervalRef.current = setInterval(fetchOrderBook, 2000);
    
    return () => {
      isMountedRef.current = false;
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [symbol, fetchOrderBook, normalizeOrderBookData]);

  // 호가 데이터 처리
  const { processedAsks, processedBids, spread, spreadPercent, highestBid, lowestAsk } = useMemo(() => {
    // 매도 호가: 낮은 가격 → 높은 가격 (위에서 아래로)
    const asks = orderBook.asks
      .slice(0, maxRows)
      .sort((a, b) => a.price - b.price);

    // 매수 호가: 높은 가격 → 낮은 가격 (위에서 아래로)
    const bids = orderBook.bids
      .slice(0, maxRows)
      .sort((a, b) => b.price - a.price);

    // 스프레드 계산
    const lowestAskPrice = asks.length > 0 ? asks[0].price : currentPrice;
    const highestBidPrice = bids.length > 0 ? bids[0].price : currentPrice;
    const spreadVal = lowestAskPrice - highestBidPrice;
    const spreadPct = highestBidPrice > 0 ? (spreadVal / highestBidPrice) * 100 : 0;

    return {
      processedAsks: asks,
      processedBids: bids,
      spread: spreadVal,
      spreadPercent: spreadPct,
      highestBid: highestBidPrice,
      lowestAsk: lowestAskPrice,
    };
  }, [orderBook, maxRows, currentPrice]);

  // 호가 클릭 핸들러
  const handlePriceClick = useCallback((price, type) => {
    setHighlightedPrice({ price, type });
    setTimeout(() => setHighlightedPrice(null), 300);
    
    if (onPriceClick) {
      onPriceClick(price);
    }
  }, [onPriceClick]);

  // 로딩 상태
  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <div className="animate-pulse">
          <div className="p-4 border-b border-gray-700">
            <div className="h-6 bg-gray-700 rounded w-1/4"></div>
          </div>
          <div className="p-4 space-y-2">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="h-8 bg-gray-700/50 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      {/* 헤더 */}
      <div className="flex items-center justify-between p-3 border-b border-gray-700 bg-gray-850">
        <h3 className="text-sm font-semibold text-gray-300">호가창</h3>
        {lastUpdate && (
          <span className="text-xs text-gray-500">
            {lastUpdate.toLocaleTimeString('ko-KR', { 
              hour: '2-digit', 
              minute: '2-digit',
              second: '2-digit'
            })}
          </span>
        )}
      </div>

      {/* 현재가 및 스프레드 */}
      <div className="px-3 py-2 bg-gray-750 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div className="text-xs">
            <span className="text-gray-400">매수: </span>
            <span className="text-green-400 font-medium">${formatPrice(highestBid)}</span>
          </div>
          <div className="text-center">
            <div className="text-sm font-bold text-white">${formatPrice(currentPrice)}</div>
            <div className="text-[10px] text-gray-400">현재가</div>
          </div>
          <div className="text-xs text-right">
            <span className="text-gray-400">매도: </span>
            <span className="text-red-400 font-medium">${formatPrice(lowestAsk)}</span>
          </div>
        </div>
        <div className="mt-1 text-center text-xs text-gray-500">
          스프레드: <span className="text-yellow-400 font-mono">{spread.toFixed(2)}</span>
          <span className="ml-1">({spreadPercent.toFixed(3)}%)</span>
        </div>
      </div>

      {/* 호가 테이블 헤더 */}
      <div className="grid grid-cols-3 text-xs text-gray-500 border-b border-gray-700">
        <div className="px-3 py-2 text-left">가격(USDT)</div>
        <div className="px-3 py-2 text-right">수량</div>
        <div className="px-3 py-2 text-right">합계</div>
      </div>

      {/* 호가 목록 */}
      <div className="max-h-[320px] overflow-y-auto">
        {/* 매도 호가 */}
        {processedAsks.map((ask, idx) => {
          const total = ask.price * ask.quantity;
          const isHighlighted = highlightedPrice?.price === ask.price && highlightedPrice?.type === 'ask';
          
          return (
            <div
              key={`ask-${idx}-${ask.price}`}
              className={`grid grid-cols-3 text-sm px-3 py-1.5 cursor-pointer transition-colors border-b border-gray-700/30
                ${isHighlighted ? 'bg-red-500/20' : 'hover:bg-gray-700/30'}`}
              onClick={() => handlePriceClick(ask.price, 'ask')}
            >
              <div className="text-red-400 font-mono text-left">
                {formatPrice(ask.price)}
              </div>
              <div className="text-gray-300 font-mono text-right">
                {ask.quantity.toFixed(6)}
              </div>
              <div className="text-gray-400 font-mono text-right">
                {total.toFixed(2)}
              </div>
            </div>
          );
        })}
        
        {/* 구분선 */}
        <div className="px-3 py-1 border-t border-b border-gray-700 bg-gray-750 text-center">
          <div className="text-xs text-gray-400">━━━━━━━━━━</div>
        </div>
        
        {/* 매수 호가 */}
        {processedBids.map((bid, idx) => {
          const total = bid.price * bid.quantity;
          const isHighlighted = highlightedPrice?.price === bid.price && highlightedPrice?.type === 'bid';
          
          return (
            <div
              key={`bid-${idx}-${bid.price}`}
              className={`grid grid-cols-3 text-sm px-3 py-1.5 cursor-pointer transition-colors border-b border-gray-700/30
                ${isHighlighted ? 'bg-green-500/20' : 'hover:bg-gray-700/30'}`}
              onClick={() => handlePriceClick(bid.price, 'bid')}
            >
              <div className="text-green-400 font-mono text-left">
                {formatPrice(bid.price)}
              </div>
              <div className="text-gray-300 font-mono text-right">
                {bid.quantity.toFixed(6)}
              </div>
              <div className="text-gray-400 font-mono text-right">
                {total.toFixed(2)}
              </div>
            </div>
          );
        })}
      </div>

      {/* 요약 */}
      <div className="px-3 py-2 border-t border-gray-700 bg-gray-750 text-xs">
        <div className="flex justify-between text-gray-400">
          <div>
            <span className="text-red-400">매도: </span>
            <span>{processedAsks.reduce((sum, a) => sum + a.quantity, 0).toFixed(6)}</span>
          </div>
          <div>
            <span className="text-green-400">매수: </span>
            <span>{processedBids.reduce((sum, b) => sum + b.quantity, 0).toFixed(6)}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OrderBook;