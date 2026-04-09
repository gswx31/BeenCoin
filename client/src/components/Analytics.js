import React, { useState, useEffect } from 'react';
import api from '../api';
import { formatUSD, toNum } from '../utils';
import { Line } from 'react-chartjs-2';
import { toast } from 'react-toastify';

const StatBox = ({ icon, label, value, sub, color = 'text-white' }) => (
  <div className="bg-dark-800 rounded-2xl p-4 border border-dark-600">
    <div className="flex items-center space-x-1.5 mb-1">
      <span className="text-xs">{icon}</span>
      <p className="text-muted text-[10px]">{label}</p>
    </div>
    <p className={`text-lg font-bold font-mono ${color}`}>{value}</p>
    {sub && <p className="text-[10px] text-dark-400 mt-0.5">{sub}</p>}
  </div>
);

const Analytics = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/analytics').then(({ data }) => setData(data)).catch(() => toast.error('분석 데이터를 불러올 수 없어요')).finally(() => setLoading(false));
  }, []);

  if (loading || !data) return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">{[1,2,3,4,5,6,7,8].map(i => <div key={i} className="skeleton h-20 rounded-2xl" />)}</div>
      <div className="skeleton h-64 rounded-2xl" />
    </div>
  );

  const pnlData = data.daily_pnl || [];
  const chartData = {
    labels: pnlData.map(d => d.date.slice(5)),
    datasets: [
      { label: '누적 손익', data: pnlData.map(d => d.pnl), borderColor: pnlData.length && pnlData[pnlData.length-1].pnl >= 0 ? '#3fb68b' : '#f0616d', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 2, tension: 0.3 },
      { label: '일별 손익', data: pnlData.map(d => d.daily), borderColor: 'rgba(247,147,26,0.5)', backgroundColor: (ctx) => ctx.raw >= 0 ? 'rgba(63,182,139,0.3)' : 'rgba(240,97,109,0.3)', borderWidth: 1, type: 'bar' },
    ],
  };
  const chartOpts = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { labels: { color: '#8b949e', font: { size: 10 } } } },
    scales: {
      x: { grid: { display: false }, ticks: { color: '#484f58', font: { size: 9 } } },
      y: { position: 'right', grid: { color: 'rgba(43,49,57,0.3)' }, ticks: { color: '#484f58', font: { size: 9 }, callback: v => '$' + v.toLocaleString() } },
    },
  };

  const wr = data.win_rate;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 fade-in">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-white">📊 거래 분석</h2>
        <div className="flex items-center space-x-2 bg-dark-800 rounded-xl px-4 py-2 border border-dark-600">
          <span className="text-lg">🔥</span>
          <div>
            <p className="text-white text-sm font-bold font-mono">{data.current_streak}일 연승중</p>
            <p className="text-dark-400 text-[9px]">최고: {data.best_streak}일</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <StatBox icon="🎯" label="승률" value={`${wr}%`} color={wr >= 50 ? 'text-profit' : 'text-loss'} sub={`${data.win_count}승 / ${data.loss_count}패`} />
        <StatBox icon="⚖️" label="손익비" value={`${data.risk_reward_ratio}:1`} color={data.risk_reward_ratio >= 1 ? 'text-profit' : 'text-loss'} />
        <StatBox icon="💪" label="수익 팩터" value={data.profit_factor.toFixed(2)} color={data.profit_factor >= 1 ? 'text-profit' : 'text-loss'} />
        <StatBox icon="📉" label="최대 낙폭" value={formatUSD(data.max_drawdown)} color="text-loss" />
        <StatBox icon="📝" label="총 거래" value={`${data.total_trades}회`} />
        <StatBox icon="✅" label="청산 거래" value={`${data.total_closed}회`} />
        <StatBox icon="💚" label="평균 수익" value={formatUSD(data.avg_win)} color="text-profit" />
        <StatBox icon="💔" label="평균 손실" value={formatUSD(data.avg_loss)} color="text-loss" />
      </div>

      {pnlData.length > 0 && (
        <div className="bg-dark-800 rounded-2xl border border-dark-600 p-5 mb-6">
          <h3 className="text-sm font-semibold text-white mb-3">📈 손익 곡선</h3>
          <div className="h-56"><Line data={chartData} options={chartOpts} /></div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-dark-800 rounded-2xl border border-dark-600">
          <div className="px-5 py-3 border-b border-dark-600"><h3 className="text-sm font-semibold text-profit">💚 최고의 거래 TOP 5</h3></div>
          {data.best_trades.length === 0 ? <div className="p-6 text-center text-muted text-sm">아직 청산 거래가 없어요</div> : (
            <div className="divide-y divide-dark-600">
              {data.best_trades.map((t, i) => (
                <div key={i} className="flex items-center justify-between px-5 py-3">
                  <div><p className="text-white text-sm font-medium">{t.symbol}</p><p className="text-dark-400 text-[10px]">{t.quantity}개 @ {formatUSD(t.price)}</p></div>
                  <span className="text-profit font-mono font-medium text-sm">+{formatUSD(t.pnl)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-dark-800 rounded-2xl border border-dark-600">
          <div className="px-5 py-3 border-b border-dark-600"><h3 className="text-sm font-semibold text-loss">💔 최악의 거래 TOP 5</h3></div>
          {data.worst_trades.length === 0 ? <div className="p-6 text-center text-muted text-sm">아직 청산 거래가 없어요</div> : (
            <div className="divide-y divide-dark-600">
              {data.worst_trades.map((t, i) => (
                <div key={i} className="flex items-center justify-between px-5 py-3">
                  <div><p className="text-white text-sm font-medium">{t.symbol}</p><p className="text-dark-400 text-[10px]">{t.quantity}개 @ {formatUSD(t.price)}</p></div>
                  <span className="text-loss font-mono font-medium text-sm">{formatUSD(t.pnl)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {Object.keys(data.symbol_stats).length > 0 && (
        <div className="bg-dark-800 rounded-2xl border border-dark-600 mt-6">
          <div className="px-5 py-3 border-b border-dark-600"><h3 className="text-sm font-semibold text-white">🪙 코인별 분석</h3></div>
          <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-dark-600">
            {Object.entries(data.symbol_stats).map(([symbol, stats]) => (
              <div key={symbol} className="p-4 text-center">
                <p className="text-accent font-bold mb-1">{symbol.replace('USDT', '')}</p>
                <p className="text-white font-mono text-sm">{formatUSD(stats.volume)} 거래량</p>
                <p className={`text-xs font-mono ${stats.pnl >= 0 ? 'text-profit' : 'text-loss'}`}>{stats.pnl >= 0 ? '+' : ''}{formatUSD(stats.pnl)}</p>
                <p className="text-dark-400 text-[10px] mt-1">{stats.buys}매수 / {stats.sells}매도</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Analytics;
