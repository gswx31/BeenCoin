import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../api';
import { formatUSD, formatPercent, toNum, getWsUrl, signedFormat } from '../utils';
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
  Filler,
} from 'chart.js';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

const WS_RECONNECT_DELAY = 3000;
const MAX_CHART_POINTS = 40;

const SkeletonCard = () => (
  <div className="bg-dark-800 rounded-xl p-5 border border-dark-600">
    <div className="skeleton h-3 w-20 mb-3" />
    <div className="skeleton h-7 w-32" />
  </div>
);

const StatCard = ({ label, value, sub, color = 'text-white' }) => (
  <div className="bg-dark-800 rounded-xl p-5 border border-dark-600 fade-in">
    <p className="text-muted text-xs font-medium uppercase tracking-wider mb-1">{label}</p>
    <p className={`text-xl font-bold font-mono ${color}`}>{value}</p>
    {sub && <p className={`text-xs mt-1 ${color} opacity-70`}>{sub}</p>}
  </div>
);

const Dashboard = () => {
  const [account, setAccount] = useState(null);
  const [priceData, setPriceData] = useState({ labels: [], prices: [] });
  const [currentPrice, setCurrentPrice] = useState(null);
  const [prevPrice, setPrevPrice] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [recentOrders, setRecentOrders] = useState([]);
  const navigate = useNavigate();
  const wsRef = useRef(null);
  const reconnectRef = useRef(null);

  const fetchData = useCallback(async () => {
    try {
      const [accRes, ordRes] = await Promise.all([
        api.get('/account'),
        api.get('/orders'),
      ]);
      setAccount(accRes.data);
      setRecentOrders(ordRes.data.slice(0, 5));
    } catch {
      toast.error('Failed to load data');
    }
  }, []);

  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(getWsUrl('/ws/prices/BTCUSDT'));
    wsRef.current = ws;

    ws.onopen = () => setWsConnected(true);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const price = parseFloat(data.price);
      setCurrentPrice((prev) => {
        setPrevPrice(prev);
        return price;
      });
      setPriceData((prev) => ({
        labels: [...prev.labels, new Date().toLocaleTimeString('en-US', { hour12: false })].slice(-MAX_CHART_POINTS),
        prices: [...prev.prices, price].slice(-MAX_CHART_POINTS),
      }));
    };

    ws.onclose = () => {
      setWsConnected(false);
      reconnectRef.current = setTimeout(connectWebSocket, WS_RECONNECT_DELAY);
    };

    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    fetchData();
    connectWebSocket();
    const interval = setInterval(fetchData, 30000);
    return () => {
      clearInterval(interval);
      clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [fetchData, connectWebSocket]);

  const priceChange = currentPrice && prevPrice ? currentPrice - prevPrice : 0;
  const priceUp = priceChange >= 0;

  const chartData = {
    labels: priceData.labels,
    datasets: [{
      label: 'BTC/USDT',
      data: priceData.prices,
      borderColor: priceUp ? '#0ecb81' : '#f6465d',
      backgroundColor: (ctx) => {
        const chart = ctx.chart;
        const { ctx: c, chartArea } = chart;
        if (!chartArea) return 'transparent';
        const gradient = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
        const baseColor = priceUp ? '14,203,129' : '246,70,93';
        gradient.addColorStop(0, `rgba(${baseColor},0.15)`);
        gradient.addColorStop(1, `rgba(${baseColor},0)`);
        return gradient;
      },
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 5,
      pointHoverBackgroundColor: '#fff',
      pointHoverBorderColor: priceUp ? '#0ecb81' : '#f6465d',
      pointHoverBorderWidth: 2,
      tension: 0.4,
      fill: true,
    }],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { intersect: false, mode: 'index' },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#1e2329',
        borderColor: '#474d57',
        borderWidth: 1,
        titleColor: '#848e9c',
        bodyColor: '#eaecef',
        bodyFont: { family: 'monospace' },
        displayColors: false,
        padding: 12,
        callbacks: {
          label: (ctx) => `  ${formatUSD(ctx.parsed.y)}`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#474d57', font: { size: 10 }, maxTicksLimit: 6 },
        border: { display: false },
      },
      y: {
        position: 'right',
        grid: { color: 'rgba(43,49,57,0.3)', drawBorder: false },
        ticks: {
          color: '#474d57',
          font: { size: 10, family: 'monospace' },
          callback: (v) => '$' + v.toLocaleString(),
        },
        border: { display: false },
      },
    },
  };

  if (!account) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[1,2,3,4].map(i => <SkeletonCard key={i} />)}
        </div>
        <div className="skeleton h-80 w-full rounded-xl" />
      </div>
    );
  }

  const profit = toNum(account.total_profit);
  const rate = toNum(account.profit_rate);
  const positions = account.positions || [];
  const positionCount = positions.length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <StatCard label="Available Balance" value={formatUSD(account.balance)} />
        <StatCard
          label="Total P&L"
          value={signedFormat(account.total_profit)}
          color={profit >= 0 ? 'text-profit' : 'text-loss'}
        />
        <StatCard
          label="Return"
          value={signedFormat(account.profit_rate, formatPercent)}
          color={rate >= 0 ? 'text-profit' : 'text-loss'}
        />
        <StatCard
          label="Total Assets"
          value={formatUSD(account.total_value)}
          sub={`${positionCount} position${positionCount !== 1 ? 's' : ''}`}
        />
      </div>

      {/* Chart */}
      <div className="bg-dark-800 rounded-xl border border-dark-600 p-5 mb-6 fade-in">
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <h3 className="text-base font-semibold text-white">BTC / USDT</h3>
              <span className={`flex items-center space-x-1 text-xs ${wsConnected ? 'text-profit' : 'text-loss'}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-profit pulse-dot' : 'bg-loss'}`} />
                <span>{wsConnected ? 'LIVE' : 'OFFLINE'}</span>
              </span>
            </div>
            {currentPrice !== null && (
              <div className="flex items-baseline space-x-2">
                <span className="text-2xl font-bold text-white font-mono">
                  {formatUSD(currentPrice)}
                </span>
                <span className={`text-sm font-medium font-mono ${priceUp ? 'text-profit' : 'text-loss'}`}>
                  {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)}
                </span>
              </div>
            )}
          </div>
        </div>
        <div className="h-64 sm:h-72">
          <Line data={chartData} options={chartOptions} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Positions Summary */}
        <div className="bg-dark-800 rounded-xl border border-dark-600 fade-in">
          <div className="flex items-center justify-between px-5 py-4 border-b border-dark-600">
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider">Positions</h3>
            <button
              onClick={() => navigate('/portfolio')}
              className="text-xs text-accent hover:text-accent-hover transition-colors"
            >
              View All
            </button>
          </div>
          {positions.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-muted text-sm mb-3">No open positions</p>
              <button
                onClick={() => navigate('/order')}
                className="text-xs text-accent hover:text-accent-hover font-medium transition-colors"
              >
                Place your first trade
              </button>
            </div>
          ) : (
            <div className="divide-y divide-dark-600">
              {positions.slice(0, 5).map((pos, i) => {
                const pnl = toNum(pos.unrealized_profit);
                return (
                  <div key={i} className="flex items-center justify-between px-5 py-3 hover:bg-dark-700 transition-colors">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-accent/15 rounded-full flex items-center justify-center">
                        <span className="text-accent text-xs font-bold">
                          {pos.symbol.replace('USDT', '').slice(0, 3)}
                        </span>
                      </div>
                      <div>
                        <p className="text-white text-sm font-medium">{pos.symbol}</p>
                        <p className="text-muted text-xs font-mono">{toNum(pos.quantity).toFixed(4)} qty</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-white text-sm font-mono">{formatUSD(pos.current_value)}</p>
                      <p className={`text-xs font-mono ${pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                        {pnl >= 0 ? '+' : ''}{formatUSD(pos.unrealized_profit)}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Recent Orders */}
        <div className="bg-dark-800 rounded-xl border border-dark-600 fade-in">
          <div className="flex items-center justify-between px-5 py-4 border-b border-dark-600">
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider">Recent Orders</h3>
            <button
              onClick={() => navigate('/history')}
              className="text-xs text-accent hover:text-accent-hover transition-colors"
            >
              View All
            </button>
          </div>
          {recentOrders.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-muted text-sm">No orders yet</p>
            </div>
          ) : (
            <div className="divide-y divide-dark-600">
              {recentOrders.map((order) => (
                <div key={order.id} className="flex items-center justify-between px-5 py-3 hover:bg-dark-700 transition-colors">
                  <div className="flex items-center space-x-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                      order.side === 'BUY' ? 'bg-profit/15 text-profit' : 'bg-loss/15 text-loss'
                    }`}>
                      {order.side}
                    </span>
                    <div>
                      <p className="text-white text-sm font-medium">{order.symbol}</p>
                      <p className="text-muted text-xs">{order.order_type} &middot; {toNum(order.quantity).toFixed(4)}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      order.order_status === 'FILLED' ? 'bg-profit/15 text-profit' :
                      order.order_status === 'CANCELLED' ? 'bg-dark-600 text-muted' :
                      'bg-accent/15 text-accent'
                    }`}>
                      {order.order_status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
