// client/src/components/trading/TradingChart.js
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
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const TradingChart = ({ symbol }) => {
  const [chartData, setChartData] = useState(null);
  const [interval, setInterval] = useState('1h');

  useEffect(() => {
    fetchChartData();
  }, [symbol, interval]);

  const fetchChartData = async () => {
    try {
      const response = await axios.get(`/api/v1/market/historical/${symbol}?interval=${interval}&limit=24`);
      const data = response.data;

      setChartData({
        labels: data.map((d) => new Date(d.timestamp).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })),
        datasets: [
          {
            label: '가격 (USDT)',
            data: data.map((d) => d.close),
            borderColor: '#4fd1c5',
            backgroundColor: 'rgba(79, 209, 197, 0.1)',
            tension: 0.4,
            fill: true,
          },
        ],
      });
    } catch (error) {
      console.error('Failed to fetch chart data:', error);
    }
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: '#fff',
        bodyColor: '#fff',
        borderColor: '#4fd1c5',
        borderWidth: 1,
      },
    },
    scales: {
      y: {
        grid: {
          color: 'rgba(255, 255, 255, 0.1)',
        },
        ticks: {
          color: '#9ca3af',
        },
      },
      x: {
        grid: {
          color: 'rgba(255, 255, 255, 0.1)',
        },
        ticks: {
          color: '#9ca3af',
        },
      },
    },
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">가격 차트</h2>
        <div className="flex space-x-2">
          {['1h', '4h', '1d'].map((int) => (
            <button
              key={int}
              onClick={() => setInterval(int)}
              className={`px-3 py-1 rounded ${interval === int ? 'bg-accent text-white' : 'bg-gray-700 text-gray-400'}`}
            >
              {int}
            </button>
          ))}
        </div>
      </div>
      <div style={{ height: '400px' }}>
        {chartData ? <Line data={chartData} options={options} /> : <div className="text-center py-20">차트를 불러오는 중...</div>}
      </div>
    </div>
  );
};

export default TradingChart;