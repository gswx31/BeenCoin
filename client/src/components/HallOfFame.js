import React, { useEffect, useState } from 'react';
import api from '../api';
import { formatUSD } from '../utils';

const HallOfFame = () => {
  const [current, setCurrent] = useState(null);
  const [hof, setHof] = useState([]);
  const [countdown, setCountdown] = useState('');

  useEffect(() => {
    api.get('/seasons/current').then(({ data }) => setCurrent(data)).catch(() => {});
    api.get('/seasons/hall-of-fame').then(({ data }) => setHof(data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!current) return;
    const id = setInterval(() => {
      let s = current.seconds_remaining - Math.floor((Date.now() - performance.timeOrigin) / 1000);
      if (s < 0) s = 0;
      const days = Math.floor(s / 86400);
      const hours = Math.floor((s % 86400) / 3600);
      const mins = Math.floor((s % 3600) / 60);
      setCountdown(`${days}일 ${hours}시간 ${mins}분`);
    }, 1000);
    return () => clearInterval(id);
  }, [current]);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 fade-in">
      <h2 className="text-xl font-bold text-white mb-6">👑 명예의 전당</h2>

      {/* 현재 시즌 */}
      {current && (
        <div className="bg-gradient-to-br from-accent/10 to-mint/10 rounded-3xl border border-accent/20 p-6 mb-6">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <p className="text-accent text-sm font-bold">{current.name}</p>
              <p className="text-white text-2xl font-bold mt-1">진행중 시즌</p>
            </div>
            <div className="text-right">
              <p className="text-muted text-[10px]">남은 시간</p>
              <p className="text-mint text-xl font-mono font-bold">{countdown || '계산중...'}</p>
            </div>
          </div>
          <p className="text-dark-400 text-xs mt-3">
            🏆 시즌 종료 시 상위 100명이 명예의 전당에 영구 기록됩니다
          </p>
        </div>
      )}

      {/* 역대 우승자 */}
      <div className="bg-dark-800 rounded-2xl border border-dark-600 overflow-hidden">
        <div className="px-5 py-3 border-b border-dark-600">
          <h3 className="text-sm font-semibold text-white">🏆 역대 시즌 우승자</h3>
        </div>
        {hof.length === 0 ? (
          <div className="p-12 text-center text-muted">
            <div className="text-4xl mb-3">👑</div>
            <p>아직 종료된 시즌이 없어요</p>
            <p className="text-dark-500 text-xs mt-1">첫 번째 우승자가 되어보세요!</p>
          </div>
        ) : (
          <div className="divide-y divide-dark-600">
            {hof.map((s) => (
              <div key={s.season_id} className="flex items-center justify-between px-5 py-4">
                <div className="flex items-center space-x-4">
                  <span className="text-2xl">🥇</span>
                  <div>
                    <p className="text-white font-bold text-sm">{s.winner.username}</p>
                    <p className="text-dark-400 text-[10px]">{s.season_name} · {new Date(s.end_date).toLocaleDateString('ko-KR')}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`font-mono font-bold text-sm ${s.winner.return_pct >= 0 ? 'text-profit' : 'text-loss'}`}>
                    {s.winner.return_pct >= 0 ? '+' : ''}{s.winner.return_pct}%
                  </p>
                  <p className="text-muted text-[10px] font-mono">{formatUSD(s.winner.total_profit)}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default HallOfFame;
