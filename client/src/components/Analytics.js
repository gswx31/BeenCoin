import React, { useState, useEffect } from 'react';
import api from '../api';
import { formatUSD, toNum } from '../utils';
import { Line } from 'react-chartjs-2';
import { toast } from 'react-toastify';

const StatBox = ({ label, value, sub, color = 'text-white' }) => (
  <div className="bg-dark-800 rounded-xl p-4 border border-dark-600">
    <p className="text-muted text-[10px] uppercase tracking-wider mb-1">{label}</p>
    <p className={`text-lg font-bold font-mono ${color}`}>{value}</p>
    {sub && <p className="text-[10px] text-dark-400 mt-0.5">{sub}</p>}
  </div>
);

const Analytics = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/analytics').then(({ data }) => setData(data)).catch(() => toast.error('Failed to load analytics')).finally(() => setLoading(false));
  }, []);

  if (loading || !data) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          {[1,2,3,4,5,6,7,8].map(i => <div key={i} className="skeleton h-20 rounded-xl" />)}
        </div>
        <div className="skeleton h-64 rounded-xl" />
      </div>
    );
  }

  const pnlData = data.daily_pnl || [];
  const chartData = {
    labels: pnlData.map(d => d.date.slice(5)),
    datasets: [
      {
        label: 'Cumulative P&L',
        data: pnlData.map(d => d.pnl),
        borderColor: pnlData.length && pnlData[pnlData.length - 1].pnl >= 0 ? '#0ecb81' : '#f6465d',
        backgroundColor: 'transparent',
        borderWidth: 2, pointRadius: 2, tension: 0.3,
      },
      {
        label: 'Daily P&L',
        data: pnlData.map(d => d.daily),
        borderColor: 'rgba(240,185,11,0.5)',
        backgroundColor: (ctx) => {
          const v = ctx.raw;
          return v >= 0 ? 'rgba(14,203,129,0.3)' : 'rgba(246,70,93,0.3)';
        },
        borderWidth: 1, type: 'bar',
      },
    ],
  };
  const chartOpts = {
    responsive: true, maintainAspectRatio: false,
    interaction: { intersect: false, mode: 'index' },
    plugins: { legend: { display: true, labels: { color: '#848e9c', font: { size: 10 } } } },
    scales: {
      x: { grid: { display: false }, ticks: { color: '#474d57', font: { size: 9 } }, border: { display: false } },
      y: { position: 'right', grid: { color: 'rgba(43,49,57,0.3)' }, ticks: { color: '#474d57', font: { size: 9 }, callback: v => '$' + v.toLocaleString() }, border: { display: false } },
    },
  };

  const wr = data.win_rate;
  const wrColor = wr >= 50 ? 'text-profit' : 'text-loss';

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 fade-in">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-white">Trading Analytics</h2>
        {/* Streak */}
        <div className="flex items-center space-x-2 bg-dark-800 rounded-lg px-4 py-2 border border-dark-600">
          <span className="text-accent text-lg">🔥</span>
          <div>
            <p className="text-white text-sm font-bold font-mono">{data.current_streak} days</p>
            <p className="text-dark-400 text-[9px]">Best: {data.best_streak}</p>
          </div>
        </div>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <StatBox label="Win Rate" value={`${wr}%`} color={wrColor} sub={`${data.win_count}W / ${data.loss_count}L`} />
        <StatBox label="Risk/Reward" value={`${data.risk_reward_ratio}:1`} color={data.risk_reward_ratio >= 1 ? 'text-profit' : 'text-loss'} />
        <StatBox label="Profit Factor" value={data.profit_factor.toFixed(2)} color={data.profit_factor >= 1 ? 'text-profit' : 'text-loss'} />
        <StatBox label="Max Drawdown" value={formatUSD(data.max_drawdown)} color="text-loss" />
        <StatBox label="Total Trades" value={data.total_trades} />
        <StatBox label="Closed Trades" value={data.total_closed} />
        <StatBox label="Avg Win" value={formatUSD(data.avg_win)} color="text-profit" />
        <StatBox label="Avg Loss" value={formatUSD(data.avg_loss)} color="text-loss" />
      </div>

      {/* PnL Chart */}
      {pnlData.length > 0 && (
        <div className="bg-dark-800 rounded-xl border border-dark-600 p-5 mb-6">
          <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-3">P&L Curve</h3>
          <div className="h-56"><Line data={chartData} options={chartOpts} /></div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Best Trades */}
        <div className="bg-dark-800 rounded-xl border border-dark-600">
          <div className="px-5 py-3 border-b border-dark-600">
            <h3 className="text-sm font-semibold text-profit uppercase tracking-wider">Best Trades</h3>
          </div>
          {data.best_trades.length === 0 ? (
            <div className="p-6 text-center text-muted text-sm">No closed trades yet</div>
          ) : (
            <div className="divide-y divide-dark-600">
              {data.best_trades.map((t, i) => (
                <div key={i} className="flex items-center justify-between px-5 py-3">
                  <div>
                    <p className="text-white text-sm font-medium">{t.symbol}</p>
                    <p className="text-dark-400 text-[10px]">{t.quantity} @ {formatUSD(t.price)}</p>
                  </div>
                  <span className="text-profit font-mono font-medium text-sm">+{formatUSD(t.pnl)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Worst Trades */}
        <div className="bg-dark-800 rounded-xl border border-dark-600">
          <div className="px-5 py-3 border-b border-dark-600">
            <h3 className="text-sm font-semibold text-loss uppercase tracking-wider">Worst Trades</h3>
          </div>
          {data.worst_trades.length === 0 ? (
            <div className="p-6 text-center text-muted text-sm">No closed trades yet</div>
          ) : (
            <div className="divide-y divide-dark-600">
              {data.worst_trades.map((t, i) => (
                <div key={i} className="flex items-center justify-between px-5 py-3">
                  <div>
                    <p className="text-white text-sm font-medium">{t.symbol}</p>
                    <p className="text-dark-400 text-[10px]">{t.quantity} @ {formatUSD(t.price)}</p>
                  </div>
                  <span className="text-loss font-mono font-medium text-sm">{formatUSD(t.pnl)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Symbol breakdown */}
      {Object.keys(data.symbol_stats).length > 0 && (
        <div className="bg-dark-800 rounded-xl border border-dark-600 mt-6">
          <div className="px-5 py-3 border-b border-dark-600">
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider">By Symbol</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-dark-600">
            {Object.entries(data.symbol_stats).map(([symbol, stats]) => (
              <div key={symbol} className="p-4 text-center">
                <p className="text-accent font-bold mb-1">{symbol.replace('USDT', '')}</p>
                <p className="text-white font-mono text-sm">{formatUSD(stats.volume)} vol</p>
                <p className={`text-xs font-mono ${stats.pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                  {stats.pnl >= 0 ? '+' : ''}{formatUSD(stats.pnl)}
                </p>
                <p className="text-dark-400 text-[10px] mt-1">{stats.buys}B / {stats.sells}S</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Analytics;
