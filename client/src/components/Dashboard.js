import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import { formatUSD, formatPercent, toNum, signedFormat } from '../utils';
import TradingChart from './TradingChart';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'];

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
  const [currentPrice, setCurrentPrice] = useState(null);
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT');
  const [recentOrders, setRecentOrders] = useState([]);
  const navigate = useNavigate();

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

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handlePriceUpdate = useCallback((price) => {
    setCurrentPrice(price);
  }, []);

  if (!account) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[1,2,3,4].map(i => <SkeletonCard key={i} />)}
        </div>
        <div className="skeleton h-96 w-full rounded-xl" />
      </div>
    );
  }

  const profit = toNum(account.total_profit);
  const rate = toNum(account.profit_rate);
  const positions = account.positions || [];

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
          sub={`${positions.length} position${positions.length !== 1 ? 's' : ''}`}
        />
      </div>

      {/* Chart */}
      <div className="bg-dark-800 rounded-xl border border-dark-600 p-5 mb-6 fade-in">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-3">
            {/* Symbol selector */}
            <div className="flex space-x-1">
              {SYMBOLS.map((s) => (
                <button
                  key={s}
                  onClick={() => setSelectedSymbol(s)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    selectedSymbol === s
                      ? 'bg-accent text-dark-900'
                      : 'text-muted hover:text-white'
                  }`}
                >
                  {s.replace('USDT', '')}
                </button>
              ))}
            </div>
            {currentPrice !== null && (
              <span className="text-xl font-bold text-white font-mono">
                {formatUSD(currentPrice)}
              </span>
            )}
          </div>
        </div>
        <TradingChart symbol={selectedSymbol} onPriceUpdate={handlePriceUpdate} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Positions */}
        <div className="bg-dark-800 rounded-xl border border-dark-600 fade-in">
          <div className="flex items-center justify-between px-5 py-4 border-b border-dark-600">
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider">Positions</h3>
            <button onClick={() => navigate('/portfolio')} className="text-xs text-accent hover:text-accent-hover transition-colors">View All</button>
          </div>
          {positions.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-muted text-sm mb-3">No open positions</p>
              <button onClick={() => navigate('/order')} className="text-xs text-accent hover:text-accent-hover font-medium">Place your first trade</button>
            </div>
          ) : (
            <div className="divide-y divide-dark-600">
              {positions.slice(0, 5).map((pos, i) => {
                const pnl = toNum(pos.unrealized_profit);
                return (
                  <div key={i} className="flex items-center justify-between px-5 py-3 hover:bg-dark-700 transition-colors">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-accent/15 rounded-full flex items-center justify-center">
                        <span className="text-accent text-xs font-bold">{pos.symbol.replace('USDT', '').slice(0, 3)}</span>
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
            <button onClick={() => navigate('/history')} className="text-xs text-accent hover:text-accent-hover transition-colors">View All</button>
          </div>
          {recentOrders.length === 0 ? (
            <div className="p-8 text-center"><p className="text-muted text-sm">No orders yet</p></div>
          ) : (
            <div className="divide-y divide-dark-600">
              {recentOrders.map((order) => (
                <div key={order.id} className="flex items-center justify-between px-5 py-3 hover:bg-dark-700 transition-colors">
                  <div className="flex items-center space-x-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                      order.side === 'BUY' ? 'bg-profit/15 text-profit' : 'bg-loss/15 text-loss'
                    }`}>{order.side}</span>
                    <div>
                      <p className="text-white text-sm font-medium">{order.symbol}</p>
                      <p className="text-muted text-xs">{order.order_type} &middot; {toNum(order.quantity).toFixed(4)}</p>
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    order.order_status === 'FILLED' ? 'bg-profit/15 text-profit' :
                    order.order_status === 'CANCELLED' ? 'bg-dark-600 text-muted' :
                    'bg-accent/15 text-accent'
                  }`}>{order.order_status}</span>
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
