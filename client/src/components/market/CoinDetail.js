// client/src/components/market/CoinDetail.js
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const CoinDetail = () => {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const [coin, setCoin] = useState(null);
  const [historicalData, setHistoricalData] = useState([]);
  const [realtimePrice, setRealtimePrice] = useState(null);
  const [interval, setInterval] = useState('1h');
  const [limit, setLimit] = useState(24);
  const [loading, setLoading] = useState(true);
  const [ws, setWs] = useState(null);

  useEffect(() => {
    fetchCoinDetail();
    fetchHistoricalData();
    connectWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [symbol, interval, limit]);

  const fetchCoinDetail = async () => {
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
  };

  const fetchHistoricalData = async () => {
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
  };

  const connectWebSocket = () => {
    const websocket = new WebSocket('ws://localhost:8000/ws/realtime');
    
    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'price_update' && data.data[symbol]) {
          setRealtimePrice(parseFloat(data.data[symbol]));
        }
      } catch (error) {
        console.error('WebSocket message error:', error);
      }
    };

    setWs(websocket);
  };

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

  // 차트 데이터 포맷
  const chartData = historicalData.map(item => ({
    time: new Date(item.timestamp).toLocaleTimeString('ko-KR', { 
      hour: '2-digit', 
      minute: '2-digit' 
    }),
    price: item.close,
    volume: item.volume
  }));

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
            <p className="text-3xl font-bold">${currentPrice.toLocaleString('ko-KR')}</p>
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
              ${parseFloat(coin.high).toLocaleString('ko-KR')}
            </p>
          </div>
          <div>
            <p className="text-gray-400 text-sm mb-1">24시간 최저가</p>
            <p className="text-2xl font-bold text-red-400">
              ${parseFloat(coin.low).toLocaleString('ko-KR')}
            </p>
          </div>
        </div>
      </div>

      {/* 차트 제어 */}
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">가격 차트</h2>
          <div className="flex space-x-2">
            <select
              value={interval}
              onChange={(e) => setInterval(e.target.value)}
              className="px-3 py-2 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent"
            >
              <option value="1m">1분</option>
              <option value="5m">5분</option>
              <option value="15m">15분</option>
              <option value="1h">1시간</option>
              <option value="4h">4시간</option>
              <option value="1d">1일</option>
            </select>
            <select
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value))}
              className="px-3 py-2 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent"
            >
              <option value="24">24개</option>
              <option value="50">50개</option>
              <option value="100">100개</option>
              <option value="200">200개</option>
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
        ) : chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis 
                dataKey="time" 
                stroke="#9CA3AF"
                tick={{ fill: '#9CA3AF' }}
              />
              <YAxis 
                stroke="#9CA3AF"
                tick={{ fill: '#9CA3AF' }}
                domain={['auto', 'auto']}
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
                dataKey="price" 
                stroke="#14B8A6" 
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
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
                <th className="text-right py-3 px-4">거래량</th>
              </tr>
            </thead>
            <tbody>
              {historicalData.slice(0, 10).map((data, index) => (
                <tr key={index} className="border-b border-gray-700 hover:bg-gray-700">
                  <td className="py-3 px-4">
                    {new Date(data.timestamp).toLocaleString('ko-KR')}
                  </td>
                  <td className="text-right py-3 px-4">${data.open.toFixed(2)}</td>
                  <td className="text-right py-3 px-4 text-green-400">${data.high.toFixed(2)}</td>
                  <td className="text-right py-3 px-4 text-red-400">${data.low.toFixed(2)}</td>
                  <td className="text-right py-3 px-4 font-semibold">${data.close.toFixed(2)}</td>
                  <td className="text-right py-3 px-4 text-gray-400">
                    {data.volume.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default CoinDetail;