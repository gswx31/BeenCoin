import React, { useState, useEffect } from 'react';
import api from '../api';
import { formatUSD } from '../utils';
import { toast } from 'react-toastify';

const RARITY_STYLES = {
  common:    { bg: 'bg-dark-600', border: 'border-dark-500', text: 'text-dark-400', label: 'Common' },
  uncommon:  { bg: 'bg-blue-900/30', border: 'border-blue-700/50', text: 'text-blue-400', label: 'Uncommon' },
  rare:      { bg: 'bg-purple-900/30', border: 'border-purple-700/50', text: 'text-purple-400', label: 'Rare' },
  epic:      { bg: 'bg-amber-900/30', border: 'border-amber-600/50', text: 'text-amber-400', label: 'Epic' },
  legendary: { bg: 'bg-red-900/30', border: 'border-red-600/50', text: 'text-red-400', label: 'Legendary' },
};

const ICONS = {
  zap: '⚡', chart: '📊', dollar: '💰', crown: '👑', gem: '💎',
  target: '🎯', fire: '🔥', arrow: '↗️', whale: '🐋', moon: '🌙',
  sun: '☀️', grid: '📦', percent: '%', shield: '🛡️', star: '⭐', pie: '🥧',
};

const Achievements = () => {
  const [tab, setTab] = useState('achievements');
  const [achData, setAchData] = useState(null);
  const [missions, setMissions] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchAll = async () => {
    try {
      const [achRes, misRes] = await Promise.all([
        api.get('/achievements'),
        api.get('/achievements/missions'),
      ]);
      setAchData(achRes.data);
      setMissions(misRes.data);
    } catch {
      toast.error('Failed to load');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, []);

  const handleClaim = async (id) => {
    try {
      const { data } = await api.post(`/achievements/missions/${id}/claim`);
      if (data.error) {
        toast.error(data.error);
      } else {
        toast.success(`+${formatUSD(data.reward)} bonus claimed!`);
        fetchAll();
      }
    } catch (err) {
      toast.error('Claim failed');
    }
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {[1,2,3,4,5,6].map(i => <div key={i} className="skeleton h-20 rounded-xl mb-3" />)}
      </div>
    );
  }

  const achievements = achData?.achievements || [];
  const unlocked = achievements.filter(a => a.unlocked);
  const locked = achievements.filter(a => !a.unlocked);
  const completedMissions = missions.filter(m => m.completed);
  const activeMissions = missions.filter(m => !m.completed);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 fade-in">
      {/* Tabs */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex space-x-1 bg-dark-800 rounded-lg p-1 border border-dark-600">
          <button onClick={() => setTab('achievements')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              tab === 'achievements' ? 'bg-dark-600 text-white' : 'text-muted hover:text-white'
            }`}>
            Achievements <span className="text-[10px] text-dark-400 ml-1">{achData?.unlocked_count}/{achData?.total_count}</span>
          </button>
          <button onClick={() => setTab('missions')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              tab === 'missions' ? 'bg-dark-600 text-white' : 'text-muted hover:text-white'
            }`}>
            Daily Missions <span className="text-[10px] text-dark-400 ml-1">{completedMissions.length}/{missions.length}</span>
          </button>
        </div>
      </div>

      {/* Achievements tab */}
      {tab === 'achievements' && (
        <div>
          {/* Progress bar */}
          <div className="bg-dark-800 rounded-xl border border-dark-600 p-5 mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-white text-sm font-medium">Progress</span>
              <span className="text-accent text-sm font-mono">{achData?.unlocked_count} / {achData?.total_count}</span>
            </div>
            <div className="h-2.5 bg-dark-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-accent rounded-full transition-all duration-500"
                style={{ width: `${(achData?.unlocked_count / achData?.total_count) * 100}%` }}
              />
            </div>
          </div>

          {/* Unlocked */}
          {unlocked.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-3">Unlocked</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {unlocked.map((a) => {
                  const style = RARITY_STYLES[a.rarity] || RARITY_STYLES.common;
                  return (
                    <div key={a.key} className={`${style.bg} border ${style.border} rounded-xl p-4 transition-transform hover:scale-[1.02]`}>
                      <div className="flex items-start justify-between">
                        <div className="flex items-center space-x-3">
                          <span className="text-2xl">{ICONS[a.icon] || '🏆'}</span>
                          <div>
                            <p className="text-white font-semibold text-sm">{a.title}</p>
                            <p className="text-muted text-[11px] mt-0.5">{a.description}</p>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center justify-between mt-3">
                        <span className={`text-[9px] uppercase font-bold ${style.text}`}>{style.label}</span>
                        <span className="text-dark-400 text-[9px]">{a.unlocked_at?.slice(0, 10)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Locked */}
          {locked.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-muted uppercase tracking-wider mb-3">Locked</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {locked.map((a) => {
                  const style = RARITY_STYLES[a.rarity] || RARITY_STYLES.common;
                  return (
                    <div key={a.key} className="bg-dark-800 border border-dark-600 rounded-xl p-4 opacity-50">
                      <div className="flex items-center space-x-3">
                        <span className="text-2xl grayscale">{ICONS[a.icon] || '🏆'}</span>
                        <div>
                          <p className="text-muted font-semibold text-sm">{a.title}</p>
                          <p className="text-dark-500 text-[11px] mt-0.5">{a.description}</p>
                        </div>
                      </div>
                      <div className="mt-3">
                        <span className={`text-[9px] uppercase font-bold ${style.text}`}>{style.label}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Daily Missions tab */}
      {tab === 'missions' && (
        <div>
          <div className="bg-dark-800 rounded-xl border border-dark-600 p-5 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-white font-semibold">Today's Missions</h3>
                <p className="text-dark-400 text-xs mt-0.5">Complete missions to earn bonus funds</p>
              </div>
              <span className="text-accent text-xs font-mono">
                {completedMissions.length}/{missions.length} done
              </span>
            </div>
          </div>

          <div className="space-y-3">
            {missions.map((m) => {
              const pct = Math.min((m.current / m.target) * 100, 100);
              return (
                <div key={m.id} className={`bg-dark-800 rounded-xl border ${m.completed ? 'border-profit/30' : 'border-dark-600'} p-5 transition-all`}>
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <p className={`font-semibold text-sm ${m.completed ? 'text-profit' : 'text-white'}`}>
                        {m.completed && '✓ '}{m.title}
                      </p>
                      <p className="text-muted text-xs mt-0.5">{m.description}</p>
                    </div>
                    <div className="text-right flex-shrink-0 ml-4">
                      <p className="text-accent font-mono text-sm font-bold">+{formatUSD(m.reward)}</p>
                      {m.completed && !m.reward_claimed ? (
                        <button onClick={() => handleClaim(m.id)}
                          className="mt-1 px-3 py-1 bg-accent text-dark-900 rounded-md text-[10px] font-bold hover:bg-accent-hover active:scale-95 transition-all">
                          CLAIM
                        </button>
                      ) : m.reward_claimed ? (
                        <span className="text-dark-400 text-[10px]">Claimed</span>
                      ) : null}
                    </div>
                  </div>
                  {/* Progress bar */}
                  <div className="flex items-center space-x-3">
                    <div className="flex-1 h-2 bg-dark-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${m.completed ? 'bg-profit' : 'bg-accent'}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-muted text-[10px] font-mono w-16 text-right">
                      {m.current}/{m.target}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {missions.length === 0 && (
            <div className="bg-dark-800 rounded-xl border border-dark-600 p-12 text-center">
              <p className="text-muted">Start trading to receive daily missions!</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Achievements;
