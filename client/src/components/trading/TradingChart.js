// client/src/components/trading/TradingChart.js
// =============================================================================
// 차트 컴포넌트 - timestamp 파싱 및 툴팁 개선
// =============================================================================
import React, { useState, useEffect, useCallback } from 'react';
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
  const [rawData, setRawData] = useState([]); // 원본 데이터 저장 (툴팁용)
  const [timeInterval, setTimeInterval] = useState('1m');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 시간 단위 그룹
  const timeframes = {
    초: ['1s', '3s', '5s', '15s', '30s'],
    분: ['1m', '3m', '5m', '15m', '30m'],
    시간: ['1h', '2h', '4h', '6h', '12h'],
    일주: ['1d', '3d', '1w'],
  };

  // ⭐ timestamp 파싱 함수 (다양한 형식 지원)
  const parseTimestamp = useCallback((value) => {
    if (!value) return new Date();
    
    // 이미 Date 객체인 경우
    if (value instanceof Date) {
      return isNaN(value.getTime()) ? new Date() : value;
    }
    
    // 숫자 (밀리초 또는 초)
    if (typeof value === 'number') {
      // 13자리면 밀리초, 10자리면 초
      const timestamp = value > 9999999999 ? value : value * 1000;
      const date = new Date(timestamp);
      return isNaN(date.getTime()) ? new Date() : date;
    }
    
    // 문자열
    if (typeof value === 'string') {
      // 숫자 문자열인 경우
      if (/^\d+$/.test(value)) {
        const num = parseInt(value, 10);
        const timestamp = num > 9999999999 ? num : num * 1000;
        const date = new Date(timestamp);
        return isNaN(date.getTime()) ? new Date() : date;
      }
      
      // ISO 문자열 또는 다른 형식
      const date = new Date(value);
      return isNaN(date.getTime()) ? new Date() : date;
    }
    
    return new Date();
  }, []);

  // 시간 단위에 따른 데이터 포인트 개수
  const getDataPointLimit = useCallback((interval) => {
    if (typeof interval !== 'string') return 50;
    if (interval.includes('s')) return 60;
    if (interval.includes('m')) return 100;
    if (interval.includes('h')) return 48;
    if (interval === '1d') return 30;
    if (interval === '3d') return 30;
    if (interval === '1w') return 24;
    return 50;
  }, []);

  // X축 레이블 포맷팅 (짧게)
  const formatLabel = useCallback((date, interval) => {
    if (!(date instanceof Date) || isNaN(date.getTime())) {
      return '--:--';
    }
    
    if (typeof interval !== 'string') {
      return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
    }
    
    if (interval.includes('s')) {
      return date.toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
      });
    } else if (interval.includes('m')) {
      return date.toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    } else if (interval.includes('h')) {
      return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}시`;
    } else {
      return `${date.getMonth() + 1}/${date.getDate()}`;
    }
  }, []);

  // ⭐ 툴팁용 상세 시간 포맷팅
  const formatTooltipTime = useCallback((date) => {
    if (!(date instanceof Date) || isNaN(date.getTime())) {
      return '시간 정보 없음';
    }
    
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  }, []);

  // 차트 데이터 로드
  const fetchChartData = useCallback(async () => {
    if (!symbol) return;
    
    try {
      setLoading(true);
      setError(null);

      const limit = getDataPointLimit(timeInterval);
      
      const response = await axios.get(
        `/api/v1/market/historical/${symbol}?interval=${timeInterval}&limit=${limit}`
      );
      
      const data = response.data;

      if (!data || data.length === 0) {
        throw new Error('데이터가 없습니다');
      }

      // 원본 데이터 저장 (timestamp 파싱 포함)
      const processedData = data.map((d) => {
        // timestamp 또는 time 필드 사용
        const rawTimestamp = d.timestamp || d.time;
        const parsedDate = parseTimestamp(rawTimestamp);
        
        return {
          ...d,
          parsedDate,
          close: typeof d.close === 'number' ? d.close : parseFloat(d.close) || 0,
        };
      });
      
      setRawData(processedData);

      setChartData({
        labels: processedData.map((d) => formatLabel(d.parsedDate, timeInterval)),
        datasets: [
          {
            label: '가격 (USDT)',
            data: processedData.map((d) => d.close),
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
    } catch (err) {
      console.error('차트 데이터 로드 실패:', err);
      setError(err.message || '차트 로드 실패');
    } finally {
      setLoading(false);
    }
  }, [symbol, timeInterval, getDataPointLimit, formatLabel, parseTimestamp]);

  // 데이터 로드 및 자동 갱신
  useEffect(() => {
    fetchChartData();
    
    let updateMs = 30000;
    
    if (typeof timeInterval === 'string') {
      if (timeInterval.includes('s')) {
        updateMs = 1000;
      } else if (timeInterval.includes('m')) {
        updateMs = 5000;
      }
    }
    
    const timer = window.setInterval(fetchChartData, updateMs);
    
    return () => window.clearInterval(timer);
  }, [symbol, timeInterval, fetchChartData]);

  // ⭐ 차트 옵션 (툴팁 개선)
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
        titleColor: '#9ca3af',
        bodyColor: '#4fd1c5',
        borderColor: '#4fd1c5',
        borderWidth: 1,
        padding: 12,
        displayColors: false,
        callbacks: {
          // ⭐ 툴팁 타이틀: 상세 시간 표시
          title: (tooltipItems) => {
            if (!tooltipItems.length) return '';
            
            const index = tooltipItems[0].dataIndex;
            if (rawData[index] && rawData[index].parsedDate) {
              return formatTooltipTime(rawData[index].parsedDate);
            }
            return tooltipItems[0].label || '';
          },
          // 가격 표시
          label: (context) => {
            const price = context.parsed.y;
            return `가격: $${price.toLocaleString('en-US', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}`;
          },
          // ⭐ 추가 정보 (OHLC)
          afterLabel: (context) => {
            const index = context.dataIndex;
            if (rawData[index]) {
              const d = rawData[index];
              const lines = [];
              
              if (d.open) lines.push(`시가: $${parseFloat(d.open).toLocaleString()}`);
              if (d.high) lines.push(`고가: $${parseFloat(d.high).toLocaleString()}`);
              if (d.low) lines.push(`저가: $${parseFloat(d.low).toLocaleString()}`);
              if (d.volume) lines.push(`거래량: ${parseFloat(d.volume).toLocaleString()}`);
              
              return lines.length > 0 ? lines : null;
            }
            return null;
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
          <span className="text-sm text-gray-400">{symbol}</span>
          {loading && (
            <div className="w-4 h-4 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
          )}
        </div>
        <div className="text-xs text-gray-500">
          마우스 올리면 상세 정보
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
                  onClick={() => setTimeInterval(int)}
                  className={`px-3 py-1.5 rounded text-sm font-medium transition-all ${
                    timeInterval === int
                      ? 'bg-teal-500 text-gray-900 shadow-lg shadow-teal-500/50'
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
                className="mt-4 px-4 py-2 bg-teal-500 text-gray-900 rounded hover:bg-teal-400"
              >
                다시 시도
              </button>
            </div>
          </div>
        ) : chartData ? (
          <Line data={chartData} options={options} />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-500"></div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TradingChart;