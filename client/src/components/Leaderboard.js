import React, { useState, useEffect } from 'react';
import api from '../api';
import { formatUSD } from '../utils';
import { toast } from 'react-toastify';

const SORT_OPTIONS = [
  { key: 'profit', label: 'Profit' },
  { key: 'return_rate', label: 'Return %' },
  { key: 'win_rate', label: 'Win Rate' },
  { key: 'streak', label: 'Streak' },
  { key: 'achievements', label: 'Achievements' },
];

const rankBadge = (rank) => {
  if (rank === 1) return <span className="text-lg">🥇</span>;
  if (rank === 2) return <span className="text-lg">🥈</span>;
  if (rank === 3) return <span className="text-lg">🥉</span>;
  return <span className="text-dark-400 text-sm font-mono w-6 text-center">{rank}</span>;
};

const Leaderboard = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState('profit');

  useEffect(() => {
    setLoading(true);
    api.get(`/leaderboard?sort_by=${sortBy}`)
      .then(({ data }) => setData(data))
      .catch(() => toast.error('Failed to load leaderboard'))
      .finally(() => setLoading(false));
  }, [sortBy]);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 fade-in">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-white">Leaderboard</h2>
        <div className="flex space-x-1 bg-dark-800 rounded-lg p-1 border border-dark-600">
          {SORT_OPTIONS.map(({ key, label }) => (
            <button key={key} onClick={() => setSortBy(key)}
              className={`px-3 py-1.5 rounded-md text-[11px] font-medium transition-colors ${
                sortBy === key ? 'bg-dark-600 text-white' : 'text-muted hover:text-white'
              }`}>{label}</button>
          ))}
        </div>
      </div>

      {/* Top 3 podium */}
      {!loading && data.length >= 3 && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          {[data[1], data[0], data[2]].map((user, i) => {
            const podiumOrder = [2, 1, 3];
            const heights = ['h-28', 'h-36', 'h-24'];
            const borders = ['border-gray-400', 'border-accent', 'border-amber-700'];
            return (
              <div key={user.user_id} className="flex flex-col items-center">
                <div className={`w-12 h-12 rounded-full ${borders[i]} border-2 bg-dark-700 flex items-center justify-center mb-2`}>
                  <span className="text-white font-bold text-sm">{user.username.slice(0, 2).toUpperCase()}</span>
                </div>
                <p className="text-white font-medium text-sm truncate max-w-full">{user.username}</p>
                <p className={`text-xs font-mono ${user.total_profit >= 0 ? 'text-profit' : 'text-loss'}`}>
                  {user.total_profit >= 0 ? '+' : ''}{formatUSD(user.total_profit)}
                </p>
                <div className={`${heights[i]} w-full bg-dark-800 rounded-t-lg border-t-2 ${borders[i]} mt-2 flex items-center justify-center`}>
                  <span className="text-2xl">{['🥈', '🥇', '🥉'][i]}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Full ranking table */}
      <div className="bg-dark-800 rounded-xl border border-dark-600 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-muted animate-pulse">Loading...</div>
        ) : data.length === 0 ? (
          <div className="p-12 text-center text-muted">No traders yet</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-dark-600">
                  <th className="px-4 py-3 text-center text-[11px] font-medium text-muted uppercase w-12">#</th>
                  <th className="px-4 py-3 text-left text-[11px] font-medium text-muted uppercase">Trader</th>
                  <th className="px-4 py-3 text-right text-[11px] font-medium text-muted uppercase">Profit</th>
                  <th className="px-4 py-3 text-right text-[11px] font-medium text-muted uppercase">Return</th>
                  <th className="px-4 py-3 text-right text-[11px] font-medium text-muted uppercase hidden sm:table-cell">Win Rate</th>
                  <th className="px-4 py-3 text-right text-[11px] font-medium text-muted uppercase hidden sm:table-cell">Streak</th>
                  <th className="px-4 py-3 text-right text-[11px] font-medium text-muted uppercase hidden md:table-cell">Trades</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-600">
                {data.map((user) => (
                  <tr key={user.user_id} className={`hover:bg-dark-700/50 transition-colors ${user.rank <= 3 ? 'bg-dark-700/20' : ''}`}>
                    <td className="px-4 py-3 text-center">{rankBadge(user.rank)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center space-x-2">
                        <div className="w-7 h-7 rounded-full bg-dark-600 flex items-center justify-center flex-shrink-0">
                          <span className="text-white text-[10px] font-bold">{user.username.slice(0, 2).toUpperCase()}</span>
                        </div>
                        <span className="text-white text-sm font-medium">{user.username}</span>
                      </div>
                    </td>
                    <td className={`px-4 py-3 text-right font-mono text-sm ${user.total_profit >= 0 ? 'text-profit' : 'text-loss'}`}>
                      {user.total_profit >= 0 ? '+' : ''}{formatUSD(user.total_profit)}
                    </td>
                    <td className={`px-4 py-3 text-right font-mono text-sm ${user.return_rate >= 0 ? 'text-profit' : 'text-loss'}`}>
                      {user.return_rate >= 0 ? '+' : ''}{user.return_rate}%
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-sm text-white hidden sm:table-cell">{user.win_rate}%</td>
                    <td className="px-4 py-3 text-right hidden sm:table-cell">
                      {user.current_streak > 0 && (
                        <span className="text-accent text-xs">🔥 {user.current_streak}d</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-muted text-sm hidden md:table-cell">{user.trade_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default Leaderboard;
