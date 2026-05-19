import React, { useState, useEffect } from 'react';
import api from '../api';
import { formatUSD } from '../utils';
import { toast } from 'react-toastify';

const CheckInModal = () => {
  const [status, setStatus] = useState(null);
  const [show, setShow] = useState(false);
  const [claiming, setClaiming] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    api.get('/checkin/status').then(({ data }) => {
      setStatus(data);
      if (!data.already_checked_in) {
        setShow(true);
      }
    }).catch(() => {});
  }, []);

  const handleClaim = async () => {
    setClaiming(true);
    try {
      const { data } = await api.post('/checkin');
      setResult(data);
      if (data.is_lucky_box) {
        toast.success(`🎁 럭키박스! ${formatUSD(data.reward)} 획득!`);
      } else {
        toast.success(`✅ ${data.streak}일 연속 출석! ${formatUSD(data.reward)} 받았어요`);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || '출석 실패');
    } finally {
      setClaiming(false);
    }
  };

  if (!show || !status) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 fade-in">
      <div className="bg-dark-800 rounded-3xl border border-dark-600 p-6 max-w-md w-full">
        {!result ? (
          <>
            <div className="text-center mb-6">
              <div className="text-5xl mb-2">📅</div>
              <h2 className="text-xl font-bold text-white">오늘의 출석 체크</h2>
              <p className="text-muted text-sm mt-1">{status.current_streak}일 연속 출석중 🔥</p>
            </div>

            <div className="grid grid-cols-7 gap-2 mb-6">
              {[1, 2, 3, 4, 5, 6, 7].map((day) => {
                const isLucky = day === 7;
                const isPast = day < status.next_reward_day;
                const isToday = day === status.next_reward_day;
                const reward = status.rewards_schedule[day];
                return (
                  <div key={day}
                    className={`aspect-square rounded-xl border flex flex-col items-center justify-center text-center transition-all ${
                      isToday ? 'border-accent bg-accent-soft scale-105' :
                      isPast ? 'border-profit/30 bg-profit-soft' :
                      'border-dark-600 bg-dark-700'
                    }`}>
                    <span className="text-[9px] text-muted">{day}일</span>
                    {isLucky ? (
                      <span className="text-lg">🎁</span>
                    ) : (
                      <span className={`text-[9px] font-mono ${isToday ? 'text-accent' : 'text-dark-400'}`}>
                        ${reward / 1000}K
                      </span>
                    )}
                  </div>
                );
              })}
            </div>

            <button onClick={handleClaim} disabled={claiming}
              className="w-full py-3.5 bg-accent text-white font-semibold rounded-2xl hover:bg-accent-hover active:scale-[0.98] transition-all disabled:opacity-50">
              {claiming ? '받는중...' : status.next_reward === 'lucky_box'
                ? '🎁 럭키박스 열기'
                : `+${formatUSD(status.next_reward)} 받기`}
            </button>
            <button onClick={() => setShow(false)} className="w-full mt-2 py-2 text-muted text-xs hover:text-white">
              나중에 받기
            </button>
          </>
        ) : (
          <div className="text-center py-4 fade-in">
            <div className="text-6xl mb-4">{result.is_lucky_box ? '🎁' : '✨'}</div>
            <h2 className="text-2xl font-bold text-white mb-1">
              {result.is_lucky_box ? '럭키박스!' : `${result.streak}일 연속!`}
            </h2>
            <p className="text-accent text-3xl font-bold font-mono my-4">
              +{formatUSD(result.reward)}
            </p>
            <p className="text-muted text-sm mb-6">잔고에 추가됐어요</p>
            <button onClick={() => setShow(false)}
              className="w-full py-3 bg-dark-600 text-white font-semibold rounded-2xl hover:bg-dark-500 transition-all">
              확인
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default CheckInModal;
