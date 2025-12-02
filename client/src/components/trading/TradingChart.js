// client/src/components/trading/TradingChart.js
// =============================================================================
// 개선된 차트 컴포넌트
// - 초 단위: 1s, 3s, 5s, 15s, 30s
// - 분 단위: 1m, 3m, 5m, 15m, 30m
// - 시간 단위: 1h, 2h, 4h, 6h, 12h
// - 일/주 단위: 1d, 3d, 1w
// =============================================================================
import React, { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import axios from '../../api/axios';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const TradingChart = ({ symbol }) => {
  const [chartData, setChartData] = useState(null);
  const [interval, setInterval] = useState('1m');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 시간 단위 그룹
  const timeframes = {
    초: ['1s', '3s', '5s', '15s', '30s'],
    분: ['1m', '3m', '5m', '15m', '30m'],
    시간: ['1h', '2h', '4h', '6h', '12h'],
    일주: ['1d', '3d', '1w'],
  };

  useEffect(() => {
    fetchChartData();
    
    // 실시간 업데이트 (초 단위는 더 자주)
    const updateInterval = interval.includes('s') ? 1000 : interval.includes('m') ? 5000 : 30000;
    const timer = setInterval(fetchChartData, updateInterval);
    
    return () => clearInterval(timer);
  }, [symbol, interval]);

  const fetchChartData = async () => {
    try {
      setLoading(true);
      setError(null);

      // 데이터 포인트 개수 결정
      const limit = getDataPointLimit(interval);
      
      // API 호출 (백엔드에서 interval 지원 필요)
      const response = await axios.get(
        `/api/v1/market/historical/${symbol}?interval=${interval}&limit=${limit}`
      );
      
      const data = response.data;

      if (!data || data.length === 0) {
        throw new Error('데이터가 없습니다');
      }

      // 차트 데이터 포맷팅
      setChartData({
        labels: data.map((d) => formatTimestamp(d.timestamp, interval)),
        datasets: [
          {
            label: '가격 (USDT)',
            data: data.map((d) => d.close),
            borderColor: '#4fd1c5',
            backgroundColor: (context) => {
              const ctx = context.chart.ctx;
              const gradient = ctx.createLinearGradient(0, 0, 0, 400);
              gradient.addColorStop(0, 'rgba(79, 209, 197, 0.3)');
              gradient.addColorStop(1, 'rgba(79, 209, 197, 0)');
              return gradient;
            },
            borderWidth: 2,
            tension: 0.4,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: '#4fd1c5',
            pointHoverBorderColor: '#fff',
            pointHoverBorderWidth: 2,
          },
        ],
      });
    } catch (error) {
      console.error('차트 데이터 로드 실패:', error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  // 시간 단위에 따른 데이터 포인트 개수
  const getDataPointLimit = (interval) => {
    if (interval.includes('s')) return 60; // 초: 60개
    if (interval.includes('m')) return 100; // 분: 100개
    if (interval.includes('h')) return 48; // 시간: 48개
    if (interval === '1d') return 30; // 일: 30개
    if (interval === '3d') return 30; // 3일: 30개
    if (interval === '1w') return 24; // 주: 24개
    return 50;
  };

  // 타임스탬프 포맷팅
  const formatTimestamp = (timestamp, interval) => {
    const date = new Date(timestamp);
    
    if (interval.includes('s')) {
      // 초: 시:분:초
      return date.toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
      });
    } else if (interval.includes('m')) {
      // 분: 시:분
      return date.toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    } else if (interval.includes('h')) {
      // 시간: 월/일 시:분
      return date.toLocaleDateString('ko-KR', { 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit' 
      });
    } else {
      // 일/주: 월/일
      return date.toLocaleDateString('ko-KR', { 
        month: 'short', 
        day: 'numeric' 
      });
    }
  };

  // 차트 옵션
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        enabled: true,
        mode: 'index',
        intersect: false,
        backgroundColor: 'rgba(0, 0, 0, 0.9)',
        titleColor: '#fff',
        bodyColor: '#4fd1c5',
        borderColor: '#4fd1c5',
        borderWidth: 1,
        padding: 12,
        displayColors: false,
        callbacks: {
          label: (context) => {
            return `$${context.parsed.y.toLocaleString('en-US', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          display: false,
          drawBorder: false,
        },
        ticks: {
          color: '#9ca3af',
          maxRotation: 0,
          autoSkipPadding: 20,
          font: {
            size: 11,
          },
        },
      },
      y: {
        position: 'right',
        grid: {
          color: 'rgba(255, 255, 255, 0.05)',
          drawBorder: false,
        },
        ticks: {
          color: '#9ca3af',
          callback: (value) => {
            return '$' + value.toLocaleString('en-US', {
              minimumFractionDigits: 0,
              maximumFractionDigits: 0,
            });
          },
          font: {
            size: 11,
          },
        },
      },
    },
    animation: {
      duration: 300,
    },
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <h2 className="text-xl font-bold">가격 차트</h2>
          {loading && (
            <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          )}
        </div>
      </div>

      {/* 시간 단위 선택 탭 */}
      <div className="space-y-2 mb-4">
        {Object.entries(timeframes).map(([group, intervals]) => (
          <div key={group}>
            <div className="text-xs text-gray-500 mb-1 font-semibold">{group}</div>
            <div className="flex flex-wrap gap-2">
              {intervals.map((int) => (
                <button
                  key={int}
                  onClick={() => setInterval(int)}
                  className={`px-3 py-1.5 rounded text-sm font-medium transition-all ${
                    interval === int
                      ? 'bg-accent text-gray-900 shadow-lg shadow-accent/50'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {int}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* 차트 영역 */}
      <div style={{ height: '450px' }}>
        {error ? (
          <div className="flex items-center justify-center h-full text-red-400">
            <div className="text-center">
              <p className="text-lg mb-2">⚠️ 차트 로드 실패</p>
              <p className="text-sm text-gray-500">{error}</p>
              <button
                onClick={fetchChartData}
                className="mt-4 px-4 py-2 bg-accent text-gray-900 rounded hover:bg-accent/80"
              >
                다시 시도
              </button>
            </div>
          </div>
        ) : chartData ? (
          <Line data={chartData} options={options} />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-400">
              <div className="w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p>차트를 불러오는 중...</p>
            </div>
          </div>
        )}
      </div>

      {/* 차트 설명 */}
      <div className="mt-4 pt-4 border-t border-gray-700 text-xs text-gray-500">
        <div className="flex justify-between">
          <span>🔄 자동 업데이트 중</span>
          <span>📊 {chartData ? chartData.labels.length : 0}개 데이터 포인트</span>
        </div>
      </div>
    </div>
  );
};

export default TradingChart;