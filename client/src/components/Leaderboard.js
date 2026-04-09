import React, { useState, useEffect } from 'react';
import api from '../api';
import { formatUSD } from '../utils';
import { toast } from 'react-toastify';

const SORT_OPTIONS = [
  { key: 'profit', label: '수익' },
  { key: 'return_rate', label: '수익률' },
  { key: 'win_rate', label: '승률' },
  { key: 'streak', label: '연승' },
  { key: 'achievements', label: '업적' },
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
      .catch(() => toast.error('랭킹을 불러올 수 없어요'))
      .finally(() => setLoading(false));
  }, [sortBy]);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 fade-in">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-white">🏆 랭킹</h2>
        <div className="flex space-x-1 bg-dark-800 rounded-xl p-1 border border-dark-600">
          {SORT_OPTIONS.map(({ key, label }) => (
            <button key={key} onClick={() => setSortBy(key)}
              className={`px-3 py-1.5 rounded-lg text-[11px] font-medium transition-colors ${
                sortBy === key ? 'bg-dark-600 text-white' : 'text-muted hover:text-white'
              }`}>{label}</button>
          ))}
        </div>
      </div>

      {!loading && data.length >= 3 && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          {[data[1], data[0], data[2]].map((user, i) => {
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
                <div className={`${heights[i]} w-full bg-dark-800 rounded-t-2xl border-t-2 ${borders[i]} mt-2 flex items-center justify-center`}>
                  <span className="text-2xl">{['🥈', '🥇', '🥉'][i]}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="bg-dark-800 rounded-2xl border border-dark-600 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-muted animate-pulse">로딩중...</div>
        ) : data.length === 0 ? (
          <div className="p-12 text-center text-muted">아직 참여자가 없어요</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-dark-600">
                  <th className="px-4 py-3 text-center text-[11px] font-medium text-muted w-12">순위</th>
                  <th className="px-4 py-3 text-left text-[11px] font-medium text-muted">트레이더</th>
                  <th className="px-4 py-3 text-right text-[11px] font-medium text-muted">수익</th>
                  <th className="px-4 py-3 text-right text-[11px] font-medium text-muted">수익률</th>
                  <th className="px-4 py-3 text-right text-[11px] font-medium text-muted hidden sm:table-cell">승률</th>
                  <th className="px-4 py-3 text-right text-[11px] font-medium text-muted hidden sm:table-cell">연승</th>
                  <th className="px-4 py-3 text-right text-[11px] font-medium text-muted hidden md:table-cell">거래수</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-600">
                {data.map((user) => (
                  <tr key={user.user_id} className={`hover:bg-dark-700/50 transition-colors ${user.rank <= 3 ? 'bg-dark-700/20' : ''}`}>
                    <td className="px-4 py-3 text-center">{rankBadge(user.rank)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center space-x-2">
                        <div className="w-7 h-7 rounded-xl bg-dark-600 flex items-center justify-center">
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
                      {user.current_streak > 0 && <span className="text-accent text-xs">🔥 {user.current_streak}일</span>}
                    </td>
                    <td className="px-4 py-3 text-right text-muted text-sm hidden md:table-cell">{user.trade_count}회</td>
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
