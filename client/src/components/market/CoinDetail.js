// client/src/components/market/CoinDetail.js
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMarket } from '../../contexts/MarketContext';
import { 
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import { toast } from 'react-toastify';

const CoinDetail = () => {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const { realtimePrices } = useMarket();
  
  const [coinInfo, setCoinInfo] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [selectedInterval, setSelectedInterval] = useState('1m');
  const [chartType, setChartType] = useState('candle');
  const [loading, setLoading] = useState(true);

  // 업비트 스타일 시간 간격
  const timeIntervals = [
    { id: '1s', label: '1초', apiInterval: '1m', limit: 60 },
    { id: '5s', label: '5초', apiInterval: '1m', limit: 60 },
    { id: '10s', label: '10초', apiInterval: '1m', limit: 60 },
    { id: '30s', label: '30초', apiInterval: '1m', limit: 60 },
    { id: '1m', label: '1분', apiInterval: '1m', limit: 100 },
    { id: '3m', label: '3분', apiInterval: '3m', limit: 100 },
    { id: '5m', label: '5분', apiInterval: '5m', limit: 100 },
    { id: '15m', label: '15분', apiInterval: '15m', limit: 96 },
    { id: '30m', label: '30분', apiInterval: '30m', limit: 96 },
    { id: '1h', label: '1시간', apiInterval: '1h', limit: 168 },
    { id: '4h', label: '4시간', apiInterval: '4h', limit: 180 },
    { id: '1d', label: '1일', apiInterval: '1d', limit: 100 }
  ];

  useEffect(() => {
    fetchCoinDetail();
  }, [symbol]);

  useEffect(() => {
    fetchChartData();
  }, [symbol, selectedInterval]);

  useEffect(() => {
    if (coinInfo && realtimePrices[symbol]) {
      setCoinInfo(prev => ({
        ...prev,
        price: realtimePrices[symbol].toString()
      }));
    }
  }, [realtimePrices, symbol]);

  const fetchCoinDetail = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/market/coin/${symbol}`);
      if (!response.ok) throw new Error('Failed to fetch coin detail');
      const data = await response.json();
      setCoinInfo(data);
    } catch (error) {
      console.error('Error fetching coin detail:', error);
      toast.error('코인 정보를 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  };

  const fetchChartData = async () => {
    try {
      const config = timeIntervals.find(i => i.id === selectedInterval);
      const { apiInterval, limit } = config;
      
      const response = await fetch(
        `http://localhost:8000/api/v1/market/historical/${symbol}?interval=${apiInterval}&limit=${limit}`
      );
      
      if (!response.ok) throw new Error('Failed to fetch chart data');
      const data = await response.json();
      
      const formattedData = data.map((item, idx) => ({
        time: formatTime(item.timestamp, selectedInterval),
        open: parseFloat(item.open),
        high: parseFloat(item.high),
        low: parseFloat(item.low),
        close: parseFloat(item.close),
        volume: parseFloat(item.volume),
        color: parseFloat(item.close) >= parseFloat(item.open) ? '#22c55e' : '#ef4444'
      }));
      
      setChartData(formattedData);
      
    } catch (error) {
      console.error('Error fetching chart data:', error);
      setChartData([]);
    }
  };

  const formatTime = (timestamp, intervalId) => {
    const date = new Date(timestamp);
    const config = timeIntervals.find(i => i.id === intervalId);
    
    if (['1s', '5s', '10s', '30s', '1m', '3m', '5m'].includes(intervalId)) {
      return date.toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit'
      });
    } else if (['15m', '30m', '1h', '4h'].includes(intervalId)) {
      return date.toLocaleDateString('ko-KR', { 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit'
      });
    } else {
      return date.toLocaleDateString('ko-KR', { 
        month: 'short', 
        day: 'numeric'
      });
    }
  };

  // 캔들스틱 커스텀 렌더러
  const renderCandlestick = (props) => {
    const { x, y, width, height, payload } = props;
    if (!payload) return null;

    const { open, close, high, low } = payload;
    const isUp = close >= open;
    const color = isUp ? '#22c55e' : '#ef4444';
    
    const bodyHeight = Math.abs(close - open) * height / (high - low);
    const bodyY = Math.min(open, close) * height / (high - low);
    
    return (
      <g>
        {/* 심지 (High-Low) */}
        <line
          x1={x + width / 2}
          y1={y}
          x2={x + width / 2}
          y2={y + height}
          stroke={color}
          strokeWidth={1}
        />
        {/* 몸통 (Open-Close) */}
        <rect
          x={x}
          y={y + bodyY}
          width={width}
          height={bodyHeight || 1}
          fill={color}
          stroke={color}
        />
      </g>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  if (!coinInfo) {
    return (
      <div className="text-center py-20">
        <p className="text-xl text-gray-400">코인 정보를 찾을 수 없습니다.</p>
        <button 
          onClick={() => navigate('/')}
          className="mt-4 px-6 py-2 bg-accent rounded-lg"
        >
          홈으로 돌아가기
        </button>
      </div>
    );
  }

  const isPositive = parseFloat(coinInfo.change) >= 0;
  const currentPrice = parseFloat(coinInfo.price);

  return (
    <div className="max-w-7xl mx-auto">
      {/* 헤더 */}
      <div className="bg-gray-800 rounded-lg p-6 mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div 
              className="w-16 h-16 rounded-full flex items-center justify-center text-3xl font-bold"
              style={{ backgroundColor: coinInfo.color }}
            >
              {coinInfo.icon}
            </div>
            <div>
              <h1 className="text-3xl font-bold">{coinInfo.name}</h1>
              <p className="text-gray-400">{coinInfo.symbol}</p>
            </div>
          </div>
          <button 
            onClick={() => navigate(`/trade/${symbol}`)}
            className="px-8 py-3 bg-accent text-white rounded-lg hover:bg-teal-600 font-semibold"
          >
            거래하기
          </button>
        </div>

        {/* 가격 정보 */}
        <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-gray-400 text-sm mb-1">현재가</p>
            <p className="text-2xl font-bold">${currentPrice.toLocaleString('en-US')}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm mb-1">24시간 변동</p>
            <p className={`text-2xl font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
              {isPositive ? '+' : ''}{parseFloat(coinInfo.change).toFixed(2)}%
            </p>
          </div>
          <div>
            <p className="text-gray-400 text-sm mb-1">24시간 최고가</p>
            <p className="text-xl font-semibold">${parseFloat(coinInfo.high || 0).toLocaleString('en-US')}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm mb-1">24시간 최저가</p>
            <p className="text-xl font-semibold">${parseFloat(coinInfo.low || 0).toLocaleString('en-US')}</p>
          </div>
        </div>
      </div>

      {/* 차트 */}
      <div className="bg-gray-800 rounded-lg p-6">
        {/* 차트 컨트롤 */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4">
            <h2 className="text-xl font-bold">차트</h2>
            
            {/* 차트 타입 선택 */}
            <div className="flex space-x-2">
              <button
                onClick={() => setChartType('candle')}
                className={`px-3 py-1 rounded text-sm ${
                  chartType === 'candle' 
                    ? 'bg-accent text-white' 
                    : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                캔들
              </button>
              <button
                onClick={() => setChartType('line')}
                className={`px-3 py-1 rounded text-sm ${
                  chartType === 'line' 
                    ? 'bg-accent text-white' 
                    : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                라인
              </button>
            </div>
          </div>
        </div>

        {/* 시간 간격 선택 */}
        <div className="flex flex-wrap gap-2 mb-6">
          {timeIntervals.map(interval => (
            <button
              key={interval.id}
              onClick={() => setSelectedInterval(interval.id)}
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                selectedInterval === interval.id
                  ? 'bg-accent text-white font-semibold'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {interval.label}
            </button>
          ))}
        </div>

        {/* 차트 영역 */}
        {chartData.length > 0 ? (
          <div>
            <ResponsiveContainer width="100%" height={450}>
              <ComposedChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="time" 
                  stroke="#9CA3AF"
                  tick={{ fill: '#9CA3AF', fontSize: 12 }}
                />
                <YAxis 
                  yAxisId="price"
                  stroke="#9CA3AF"
                  tick={{ fill: '#9CA3AF', fontSize: 12 }}
                  domain={['auto', 'auto']}
                  tickFormatter={(value) => `$${value.toLocaleString()}`}
                />
                <YAxis 
                  yAxisId="volume"
                  orientation="right"
                  stroke="#9CA3AF"
                  tick={{ fill: '#9CA3AF', fontSize: 12 }}
                  tickFormatter={(value) => `${(value / 1000).toFixed(0)}K`}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1F2937', 
                    border: '1px solid #374151',
                    borderRadius: '8px'
                  }}
                  labelStyle={{ color: '#D1D5DB' }}
                  formatter={(value, name) => {
                    if (name === 'volume') return [`${value.toLocaleString()}`, '거래량'];
                    return [`$${value.toLocaleString('en-US')}`, name];
                  }}
                />
                
                {/* 차트 타입에 따라 다른 렌더링 */}
                {chartType === 'line' ? (
                  <Line 
                    yAxisId="price"
                    type="monotone" 
                    dataKey="close" 
                    stroke="#14B8A6" 
                    strokeWidth={2}
                    dot={false}
                    name="가격"
                  />
                ) : (
                  <>
                    <Line 
                      yAxisId="price"
                      type="monotone" 
                      dataKey="high" 
                      stroke="transparent"
                      dot={false}
                    />
                    <Line 
                      yAxisId="price"
                      type="monotone" 
                      dataKey="low" 
                      stroke="transparent"
                      dot={false}
                    />
                    <Bar yAxisId="price" dataKey="close" shape={<CustomCandle />} />
                  </>
                )}
                
                {/* 거래량 */}
                <Bar yAxisId="volume" dataKey="volume" opacity={0.3}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-96 flex items-center justify-center">
            <p className="text-gray-400">차트 데이터를 불러오는 중...</p>
          </div>
        )}

        {/* 거래량 정보 */}
        <div className="mt-6 pt-6 border-t border-gray-700">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-gray-400 text-sm mb-1">24시간 거래량</p>
              <p className="text-xl font-semibold">
                {parseFloat(coinInfo.volume || 0).toLocaleString('en-US', { maximumFractionDigits: 2 })} {coinInfo.name}
              </p>
            </div>
            <div>
              <p className="text-gray-400 text-sm mb-1">24시간 거래대금</p>
              <p className="text-xl font-semibold">
                ${parseFloat(coinInfo.quoteVolume || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// 캔들스틱 커스텀 컴포넌트
const CustomCandle = (props) => {
  const { x, y, width, height, payload } = props;
  if (!payload || !payload.open) return null;

  const { open, close, high, low, color } = payload;
  
  // 가격 범위
  const priceRange = high - low;
  if (priceRange === 0) return null;
  
  // 캔들 몸통
  const bodyTop = Math.max(open, close);
  const bodyBottom = Math.min(open, close);
  const bodyHeight = Math.abs(close - open);
  
  // 스케일 계산
  const scale = height / priceRange;
  
  const wickTop = y + (high - bodyTop) * scale;
  const wickBottom = y + (high - bodyBottom) * scale;
  const bodyY = y + (high - bodyTop) * scale;
  const bodyH = bodyHeight * scale || 1;
  
  return (
    <g>
      {/* 위 심지 */}
      <line
        x1={x + width / 2}
        y1={y + (high - high) * scale}
        x2={x + width / 2}
        y2={bodyY}
        stroke={color}
        strokeWidth={1}
      />
      {/* 아래 심지 */}
      <line
        x1={x + width / 2}
        y1={bodyY + bodyH}
        x2={x + width / 2}
        y2={y + (high - low) * scale}
        stroke={color}
        strokeWidth={1}
      />
      {/* 몸통 */}
      <rect
        x={x + 1}
        y={bodyY}
        width={Math.max(width - 2, 1)}
        height={bodyH}
        fill={color}
        stroke={color}
      />
    </g>
  );
};

export default CoinDetail;