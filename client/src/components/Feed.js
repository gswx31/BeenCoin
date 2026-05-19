import React, { useEffect, useState } from 'react';
import api from '../api';
import { timeAgo } from '../utils';

const ICONS = {
  TRADE: '📊', BIG_WIN: '🐋', ACHIEVEMENT: '🏆', TIER_UP: '⬆️',
};

const Feed = () => {
  const [feed, setFeed] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchFeed = () => {
    api.get('/feed').then(({ data }) => setFeed(data)).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchFeed();
    const id = setInterval(fetchFeed, 5000);  // 5초마다 갱신
    return () => clearInterval(id);
  }, []);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-6">
        {[1,2,3,4].map(i => <div key={i} className="skeleton h-16 rounded-2xl mb-2" />)}
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-6 fade-in">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-white">📡 실시간 피드</h2>
        <span className="flex items-center space-x-1 text-[10px] text-mint">
          <span className="w-1.5 h-1.5 rounded-full bg-mint pulse-dot" />
          <span>LIVE</span>
        </span>
      </div>

      {feed.length === 0 ? (
        <div className="bg-dark-800 rounded-2xl border border-dark-600 p-12 text-center">
          <div className="text-4xl mb-3">🌱</div>
          <p className="text-muted">아직 활동이 없어요</p>
          <p className="text-dark-500 text-xs mt-1">첫 거래의 주인공이 되어보세요!</p>
        </div>
      ) : (
        <div className="space-y-2">
          {feed.map((item) => (
            <div key={item.id} className="bg-dark-800 rounded-2xl border border-dark-600 p-4 flex items-center justify-between hover:border-dark-500 transition-colors">
              <div className="flex items-center space-x-3">
                <div className="w-9 h-9 rounded-xl bg-dark-700 flex items-center justify-center">
                  <span className="text-base">{ICONS[item.activity_type] || '📊'}</span>
                </div>
                <div>
                  <p className="text-white text-sm">
                    <span className="font-semibold text-accent">{item.username}</span>{' '}
                    <span className="text-muted">님이</span>
                  </p>
                  <p className="text-muted text-xs">{item.message}</p>
                </div>
              </div>
              <span className="text-dark-400 text-[10px] whitespace-nowrap">{timeAgo(item.created_at)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Feed;
