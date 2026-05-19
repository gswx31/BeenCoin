import React, { useEffect, useState } from 'react';
import api from '../api';
import { formatUSD } from '../utils';
import { toast } from 'react-toastify';

const Referral = () => {
  const [info, setInfo] = useState(null);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchInfo = () => {
    api.get('/referral/me').then(({ data }) => setInfo(data)).catch(() => {});
  };
  useEffect(() => { fetchInfo(); }, []);

  const handleCopy = () => {
    if (!info?.referral_code) return;
    navigator.clipboard.writeText(info.referral_code);
    toast.success('코드 복사 완료!');
  };

  const handleShare = () => {
    const url = `${window.location.origin}/register?code=${info.referral_code}`;
    navigator.clipboard.writeText(url);
    toast.success('초대 링크 복사 완료!');
  };

  const handleUse = async (e) => {
    e.preventDefault();
    if (!code.trim()) return;
    setLoading(true);
    try {
      const { data } = await api.post('/referral/use', { code: code.trim() });
      toast.success(`✨ ${data.referrer_username}님의 코드로 ${formatUSD(data.new_user_bonus)} 받았어요!`);
      setCode('');
      fetchInfo();
    } catch (e) {
      toast.error(e.response?.data?.detail || '실패');
    } finally {
      setLoading(false);
    }
  };

  if (!info) return null;

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-6 fade-in">
      <h2 className="text-xl font-bold text-white mb-6">🎁 친구 초대</h2>

      <div className="bg-gradient-to-br from-accent/15 to-mint/10 rounded-3xl border border-accent/30 p-6 mb-6">
        <p className="text-center text-white text-lg font-bold mb-1">친구를 초대하고 보너스 받기</p>
        <p className="text-center text-muted text-sm mb-4">
          신규 가입자 <span className="text-accent font-bold">{formatUSD(info.new_user_bonus)}</span>{' '}
          + 추천인 <span className="text-mint font-bold">{formatUSD(info.referrer_bonus)}</span>
        </p>

        <div className="bg-dark-900 rounded-2xl p-4 mb-3">
          <p className="text-muted text-[10px] uppercase tracking-wider mb-1.5">내 추천 코드</p>
          <div className="flex items-center justify-between">
            <span className="text-2xl font-bold text-accent font-mono tracking-wider">{info.referral_code}</span>
            <button onClick={handleCopy}
              className="px-3 py-1.5 bg-accent text-white text-xs font-semibold rounded-lg hover:bg-accent-hover">
              복사
            </button>
          </div>
        </div>

        <button onClick={handleShare}
          className="w-full py-2.5 bg-dark-700 text-white text-sm font-semibold rounded-xl hover:bg-dark-600 transition-colors">
          📤 초대 링크 공유
        </button>
      </div>

      {/* 통계 */}
      <div className="grid grid-cols-2 gap-3 mb-6">
        <div className="bg-dark-800 rounded-2xl border border-dark-600 p-4 text-center">
          <p className="text-muted text-[10px] mb-1">초대 성공</p>
          <p className="text-2xl font-bold text-white">{info.referral_count}명</p>
        </div>
        <div className="bg-dark-800 rounded-2xl border border-dark-600 p-4 text-center">
          <p className="text-muted text-[10px] mb-1">받은 보너스</p>
          <p className="text-2xl font-bold text-mint font-mono">{formatUSD(info.earned_bonus)}</p>
        </div>
      </div>

      {/* 코드 사용 (가입 후 1회) */}
      {!info.referred_by && (
        <div className="bg-dark-800 rounded-2xl border border-dark-600 p-5">
          <h3 className="text-sm font-semibold text-white mb-3">추천 코드 입력</h3>
          <p className="text-muted text-xs mb-3">친구의 코드를 입력하면 {formatUSD(info.new_user_bonus)} 보너스!</p>
          <form onSubmit={handleUse} className="flex space-x-2">
            <input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())}
              maxLength={8}
              placeholder="ABCD1234"
              className="flex-1 px-4 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white font-mono uppercase tracking-wider focus:outline-none focus:border-accent" />
            <button type="submit" disabled={loading || !code.trim()}
              className="px-5 py-2.5 bg-accent text-white text-sm font-semibold rounded-xl hover:bg-accent-hover disabled:opacity-50">
              {loading ? '...' : '받기'}
            </button>
          </form>
        </div>
      )}

      {info.referred_by && (
        <div className="bg-dark-800 rounded-2xl border border-dark-600 p-4 text-center">
          <p className="text-muted text-sm">
            <span className="text-accent font-semibold">{info.referred_by}</span>님의 초대로 가입했어요 ✨
          </p>
        </div>
      )}
    </div>
  );
};

export default Referral;
