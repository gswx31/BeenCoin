import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Line } from 'react-chartjs-2';
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
import { toast } from 'react-toastify';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const Dashboard = () => {
  const [account, setAccount] = useState(null);
  const [priceData, setPriceData] = useState({ labels: [], datasets: [] });
  const token = localStorage.getItem('token');

  useEffect(() => {
    const fetchAccount = async () => {
      try {
        const response = await axios.get('/api/v1/account', {
          headers: { Authorization: `Bearer ${token}` },
        });
        setAccount(response.data);
      } catch (error) {
        toast.error('계좌 정보 로드 실패');
      }
    };

    const ws = new WebSocket('ws://localhost:8000/api/v1/ws/prices/BTCUSDT');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setPriceData((prev) => {
        const newLabels = [...prev.labels, new Date().toLocaleTimeString()];
        const newData = [...(prev.datasets[0]?.data || []), parseFloat(data.price)];
        return {
          labels: newLabels.slice(-20),
          datasets: [{
            label: 'BTCUSDT Price',
            data: newData.slice(-20),
            borderColor: '#4fd1c5',
            tension: 0.1
          }]
        };
      });
    };

    fetchAccount();
    return () => ws.close();
  }, [token]);

  if (!account) return <div className="text-center mt-10">로딩 중...</div>;

  return (
    <div className="max-w-4xl mx-auto mt-10 p-6 bg-white rounded-lg shadow-xl">
      <h2 className="text-2xl font-bold mb-4">대시보드</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="p-4 bg-gray-100 rounded">
          <p className="text-sm text-gray-600">잔고</p>
          <p className="text-lg font-semibold">${account.balance.toFixed(2)}</p>
        </div>
        <div className="p-4 bg-gray-100 rounded">
          <p className="text-sm text-gray-600">총 수익</p>
          <p className={`text-lg font-semibold ${account.total_profit > 0 ? 'text-green-600' : 'text-red-600'}`}>
            ${account.total_profit.toFixed(2)}
          </p>
        </div>
        <div className="p-4 bg-gray-100 rounded">
          <p className="text-sm text-gray-600">수익률</p>
          <p className="text-lg font-semibold">{account.profit_rate.toFixed(2)}%</p>
        </div>
      </div>
      <h3 className="text-xl font-semibold mb-2">실시간 BTCUSDT 가격 차트</h3>
      <div className="bg-gray-50 p-4 rounded">
        <Line data={priceData} />
      </div>
      <div className="mt-4 flex space-x-4">
        <a href="/portfolio" className="text-accent hover:underline">포트폴리오 보기</a>
        <a href="/order" className="text-accent hover:underline">주문 하기</a>
      </div>
    </div>
  );
};

export default Dashboard;
