// client/src/components/market/CoinDetail.js
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ComposedChart, 
  Bar,
  Line,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer
} from 'recharts';

const CoinDetail = () => {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const [coin, setCoin] = useState(null);
  const [historicalData, setHistoricalData] = useState([]);
  const [realtimePrice, setRealtimePrice] = useState(null);
  const [interval, setInterval] = useState('1m');
  const [limit, setLimit] = useState(100);
  const [loading, setLoading] = useState(true);
  const [chartType, setChartType] = useState('candlestick'); // 'candlestick' or 'line'
  const wsRef = useRef(null);

  // useCallback으로 함수 래핑 (의존성 경고 해결 및 안정성 확보)
  const fetchCoinDetail = useCallback(async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/market/coin/${symbol}`);
      if (response.ok) {
        const data = await response.json();
        setCoin(data);
        setRealtimePrice(parseFloat(data.price));
      }
    } catch (error) {
      console.error('Failed to fetch coin detail:', error);
    }
  }, [symbol]);

  const fetchHistoricalData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/market/historical/${symbol}?interval=${interval}&limit=${limit}`
      );
      if (response.ok) {
        const data = await response.json();
        setHistoricalData(data);
      }
    } catch (error) {
      console.error('Failed to fetch historical data:', error);
    } finally {
      setLoading(false);
    }
  }, [symbol, interval, limit]);

  const connectWebSocket = useCallback(() => {
    const websocket = new WebSocket('ws://localhost:8000/ws/realtime');
    
    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'price_update' && data.data[symbol]) {
          const newPrice = parseFloat(data.data[symbol]);
          setRealtimePrice(newPrice);
          
          // 실시간으로 마지막 캔들 업데이트
          setHistoricalData(prev => {
            if (prev.length === 0) return prev;
            const updated = [...prev];
            const lastCandle = updated[updated.length - 1];
            updated[updated.length - 1] = {
              ...lastCandle,
              close: newPrice,
              high: Math.max(lastCandle.high, newPrice),
              low: Math.min(lastCandle.low, newPrice)
            };
            return updated;
          });
        }
      } catch (error) {
        console.error('WebSocket message error:', error);
      }
    };

    wsRef.current = websocket;
  }, [symbol]);

  const getUpdateInterval = useCallback((intervalStr) => {
    const map = {
      '1s': 1000,
      '5s': 5000,
      '15s': 15000,
      '30s': 30000,
      '1m': 60000,
      '5m': 5 * 60000,
      '15m': 15 * 60000,
      '1h': 60 * 60000,
      '4h': 4 * 60 * 60000,
      '1d': 24 * 60 * 60000,
    };
    return map[intervalStr] || 60000;
  }, []);

  useEffect(() => {
    fetchCoinDetail();
    fetchHistoricalData();
    connectWebSocket();

    // 실시간 데이터 업데이트 (선택된 interval에 따라)
    const updateInterval = getUpdateInterval(interval);
    const intervalId = setInterval(() => {
      fetchHistoricalData();
    }, updateInterval);

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      clearInterval(intervalId);
    };
  }, [symbol, interval, limit, fetchCoinDetail, fetchHistoricalData, connectWebSocket, getUpdateInterval]);

  if (!coin && loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-400">코인 정보를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (!coin) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-400">코인 정보를 찾을 수 없습니다.</p>
        <button onClick={() => navigate('/')} className="mt-4 px-4 py-2 bg-accent rounded-lg">
          대시보드로 돌아가기
        </button>
      </div>
    );
  }

  const currentPrice = realtimePrice || parseFloat(coin.price);
  const priceChange = parseFloat(coin.change);
  const isPositive = priceChange >= 0;

  // 캔들스틱 차트 데이터 포맷 (interval undefined 방지)
  const candleData = historicalData.map((item) => {
    const isUp = item.close >= item.open;
    return {
      time: new Date(item.timestamp).toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: (typeof interval === 'string' && interval?.includes('s')) ? '2-digit' : undefined
      }),
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
      volume: item.volume,
      color: isUp ? '#10b981' : '#ef4444',
      // 캔들 몸통
      candleHeight: Math.abs(item.close - item.open),
      candleY: Math.min(item.open, item.close),
      // 심지
      wickTop: item.high,
      wickBottom: item.low
    };
  });

  // 커스텀 캔들스틱 렌더러 (미사용 변수 제거, 스케일링 개선)
  const CustomCandlestick = (props) => {
    const { x, y, width, height, payload } = props;
    if (!payload || height <= 0) return null;

    const candleWidth = Math.max(width * 0.6, 2);
    const wickWidth = Math.max(width * 0.1, 1);
    const centerX = x + width / 2;

    const range = payload.high - payload.low;
    if (range <= 0) return null;

    // 몸통 픽셀 계산 (candleY와 candleHeight 사용)
    const bodyHeight = (payload.candleHeight / range) * height;
    const bodyY = y + ((payload.high - payload.candleY) / range) * height;

    return (
      <g>
        {/* 심지 (high-low) */}
        <line
          x1={centerX}
          y1={y}
          x2={centerX}
          y2={y + height}
          stroke={payload.color}
          strokeWidth={wickWidth}
        />
        {/* 몸통 (open-close) */}
        <rect
          x={centerX - candleWidth / 2}
          y={bodyY}
          width={candleWidth}
          height={Math.max(bodyHeight, 1)}
          fill={payload.color}
        />
      </g>
    );
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button 
            onClick={() => navigate('/')} 
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            ← 뒤로
          </button>
          <div 
            className="w-16 h-16 rounded-full flex items-center justify-center text-3xl font-bold"
            style={{ backgroundColor: coin.color }}
          >
            {coin.icon}
          </div>
          <div>
            <h1 className="text-3xl font-bold">{coin.name}</h1>
            <p className="text-gray-400">{coin.symbol}</p>
          </div>
        </div>
        <button 
          onClick={() => navigate(`/trade/${symbol}`)} 
          className="px-6 py-3 bg-accent hover:bg-teal-600 rounded-lg font-semibold transition-colors"
        >
          거래하기
        </button>
      </div>

      {/* 가격 정보 */}
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="text-gray-400 text-sm mb-1">현재가</p>
            <p className="text-3xl font-bold">${currentPrice.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm mb-1">24시간 변동</p>
            <p className={`text-2xl font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
              {isPositive ? '+' : ''}{priceChange.toFixed(2)}%
            </p>
          </div>
          <div>
            <p className="text-gray-400 text-sm mb-1">24시간 최고가</p>
            <p className="text-2xl font-bold text-green-400">
              ${parseFloat(coin.high).toLocaleString('ko-KR', { maximumFractionDigits: 2 })}
            </p>
          </div>
          <div>
            <p className="text-gray-400 text-sm mb-1">24시간 최저가</p>
            <p className="text-2xl font-bold text-red-400">
              ${parseFloat(coin.low).toLocaleString('ko-KR', { maximumFractionDigits: 2 })}
            </p>
          </div>
        </div>
      </div>

      {/* 차트 제어 */}
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center space-x-4">
            <h2 className="text-xl font-bold">가격 차트</h2>
            <div className="flex space-x-2">
              <button
                onClick={() => setChartType('candlestick')}
                className={`px-3 py-1 rounded ${chartType === 'candlestick' ? 'bg-accent text-white' : 'bg-gray-700 text-gray-300'}`}
              >
                캔들
              </button>
              <button
                onClick={() => setChartType('line')}
                className={`px-3 py-1 rounded ${chartType === 'line' ? 'bg-accent text-white' : 'bg-gray-700 text-gray-300'}`}
              >
                라인
              </button>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {/* 시간 간격 선택 (undefined 방지) */}
            <select
              value={interval || '1m'}
              onChange={(e) => {
                const val = e.target.value;
                if (val) setInterval(val);
              }}
              className="px-3 py-2 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent"
            >
              <option value="1s">1초</option>
              <option value="5s">5초</option>
              <option value="15s">15초</option>
              <option value="30s">30초</option>
              <option value="1m">1분</option>
              <option value="5m">5분</option>
              <option value="15m">15분</option>
              <option value="1h">1시간</option>
              <option value="4h">4시간</option>
              <option value="1d">1일</option>
            </select>
            {/* 데이터 개수 선택 */}
            <select
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value) || 100)}
              className="px-3 py-2 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent"
            >
              <option value="50">50개</option>
              <option value="100">100개</option>
              <option value="200">200개</option>
              <option value="500">500개</option>
            </select>
          </div>
        </div>
      </div>

      {/* 차트 */}
      <div className="bg-gray-800 rounded-lg p-6">
        {loading ? (
          <div className="h-96 flex items-center justify-center">
            <div className="text-center">
              <div className="w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
              <p className="text-gray-400">차트 로딩 중...</p>
            </div>
          </div>
        ) : candleData.length > 0 ? (
          <ResponsiveContainer width="100%" height={500}>
            {chartType === 'candlestick' ? (
              <ComposedChart data={candleData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="time" 
                  stroke="#9CA3AF"
                  tick={{ fill: '#9CA3AF', fontSize: 12 }}
                  interval="preserveStartEnd"
                />
                <YAxis 
                  stroke="#9CA3AF"
                  tick={{ fill: '#9CA3AF' }}
                  domain={['auto', 'auto']}
                  tickFormatter={(value) => `$${value.toFixed(2)}`}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1F2937', 
                    border: '1px solid #374151',
                    borderRadius: '8px'
                  }}
                  labelStyle={{ color: '#9CA3AF' }}
                  formatter={(value, name) => {
                    if (name === 'volume') return [value.toFixed(2), '거래량'];
                    return [`$${value.toFixed(2)}`, name];
                  }}
                />
                {/* 캔들스틱 표시 */}
                <Bar 
                  dataKey="high" 
                  fill="#8884d8"
                  shape={<CustomCandlestick />}
                />
                {/* 거래량 (하단에 작게) */}
                <Bar 
                  dataKey="volume" 
                  fill="#6b7280"
                  opacity={0.3}
                  yAxisId="volume"
                />
                <YAxis 
                  yAxisId="volume"
                  orientation="right"
                  stroke="#6b7280"
                  tick={false}
                  domain={[0, 'auto']}
                />
              </ComposedChart>
            ) : (
              <ComposedChart data={candleData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="time" 
                  stroke="#9CA3AF"
                  tick={{ fill: '#9CA3AF', fontSize: 12 }}
                />
                <YAxis 
                  stroke="#9CA3AF"
                  tick={{ fill: '#9CA3AF' }}
                  domain={['auto', 'auto']}
                  tickFormatter={(value) => `$${value.toFixed(2)}`}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1F2937', 
                    border: '1px solid #374151',
                    borderRadius: '8px'
                  }}
                  labelStyle={{ color: '#9CA3AF' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="close" 
                  stroke="#14B8A6" 
                  strokeWidth={2}
                  dot={false}
                  name="종가"
                />
              </ComposedChart>
            )}
          </ResponsiveContainer>
        ) : (
          <div className="h-96 flex items-center justify-center">
            <p className="text-gray-400">차트 데이터를 불러올 수 없습니다.</p>
          </div>
        )}
      </div>

      {/* 거래 내역 테이블 */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">최근 거래 데이터</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-3 px-4">시간</th>
                <th className="text-right py-3 px-4">시가</th>
                <th className="text-right py-3 px-4">고가</th>
                <th className="text-right py-3 px-4">저가</th>
                <th className="text-right py-3 px-4">종가</th>
                <th className="text-right py-3 px-4">변동</th>
              </tr>
            </thead>
            <tbody>
              {historicalData.slice(-20).reverse().map((data, index) => {
                const change = ((data.close - data.open) / data.open) * 100;
                const isUp = change >= 0;
                return (
                  <tr key={index} className="border-b border-gray-700 hover:bg-gray-700">
                    <td className="py-3 px-4 text-sm">
                      {new Date(data.timestamp).toLocaleString('ko-KR')}
                    </td>
                    <td className="text-right py-3 px-4">${data.open.toFixed(2)}</td>
                    <td className="text-right py-3 px-4 text-green-400">${data.high.toFixed(2)}</td>
                    <td className="text-right py-3 px-4 text-red-400">${data.low.toFixed(2)}</td>
                    <td className="text-right py-3 px-4 font-semibold">${data.close.toFixed(2)}</td>
                    <td className={`text-right py-3 px-4 ${isUp ? 'text-green-400' : 'text-red-400'}`}>
                      {isUp ? '+' : ''}{change.toFixed(2)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default CoinDetail;