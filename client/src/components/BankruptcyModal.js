import React, { useState, useEffect } from 'react';
import api from '../api';
import { formatUSD } from '../utils';
import { toast } from 'react-toastify';

const BankruptcyModal = ({ open, onClose, onSuccess }) => {
  const [status, setStatus] = useState(null);
  const [applying, setApplying] = useState(false);
  const [confirm, setConfirm] = useState(false);

  useEffect(() => {
    if (open) {
      api.get('/bankruptcy/status').then(({ data }) => setStatus(data)).catch(() => {});
    }
  }, [open]);

  if (!open) return null;

  const handleApply = async () => {
    setApplying(true);
    try {
      const { data } = await api.post('/bankruptcy/apply');
      toast.success(`🆘 다시 시작했어요! 잔고 ${formatUSD(data.new_balance)} 충전됨`);
      onSuccess?.();
      onClose();
    } catch (e) {
      toast.error(e.response?.data?.detail || '신청 실패');
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 fade-in">
      <div className="bg-dark-800 rounded-3xl border border-dark-600 p-6 max-w-md w-full">
        <div className="text-center mb-6">
          <div className="text-5xl mb-3">🆘</div>
          <h2 className="text-xl font-bold text-white mb-2">파산 신청</h2>
          <p className="text-muted text-sm leading-relaxed">
            자산이 거의 다 떨어졌나요?<br/>한 번 더 도전할 기회를 드릴게요.
          </p>
        </div>

        {status && (
          <div className="bg-dark-900 rounded-2xl p-4 mb-4 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted">현재 총 자산</span>
              <span className="text-white font-mono">{formatUSD(status.total_assets)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">신청 가능 기준</span>
              <span className="text-white font-mono">~ {formatUSD(status.threshold)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">지금까지 파산 횟수</span>
              <span className="text-loss font-bold">{status.bankruptcy_count}회</span>
            </div>
            {status.cooldown_remaining_days > 0 && (
              <div className="flex justify-between border-t border-dark-600 pt-2">
                <span className="text-loss">대기 시간</span>
                <span className="text-loss font-bold">{status.cooldown_remaining_days}일 남음</span>
              </div>
            )}
          </div>
        )}

        {status?.can_apply ? (
          <div className="bg-mint/10 border border-mint/30 rounded-2xl p-4 mb-4 text-xs">
            <p className="text-mint font-bold mb-1">✨ 신청 가능해요</p>
            <ul className="text-muted space-y-1">
              <li>• 잔고를 $1,000,000으로 리셋해요</li>
              <li>• 모든 보유 포지션은 정리돼요</li>
              <li>• 통계, 업적, 티어는 그대로 유지돼요</li>
              <li>• 다음 신청은 7일 후에 가능해요</li>
            </ul>
          </div>
        ) : (
          <div className="bg-dark-700 rounded-2xl p-4 mb-4 text-xs text-muted">
            {status?.cooldown_remaining_days > 0
              ? `최근 파산 후 ${status.cooldown_remaining_days}일이 더 지나야 다시 신청할 수 있어요.`
              : `총 자산이 ${formatUSD(status?.threshold || 10000)} 미만일 때만 신청 가능해요.`}
          </div>
        )}

        {status?.can_apply && !confirm && (
          <>
            <button onClick={() => setConfirm(true)}
              className="w-full py-3 bg-loss text-white font-semibold rounded-2xl hover:bg-loss/90">
              파산 신청하기
            </button>
            <button onClick={onClose} className="w-full mt-2 py-2 text-muted text-xs hover:text-white">
              취소
            </button>
          </>
        )}

        {confirm && (
          <>
            <p className="text-loss text-center text-sm mb-3">정말로 파산을 신청하시겠어요?</p>
            <div className="grid grid-cols-2 gap-2">
              <button onClick={() => setConfirm(false)}
                className="py-3 bg-dark-700 text-white text-sm font-semibold rounded-2xl">
                돌아가기
              </button>
              <button onClick={handleApply} disabled={applying}
                className="py-3 bg-loss text-white text-sm font-semibold rounded-2xl disabled:opacity-50">
                {applying ? '처리중...' : '확인'}
              </button>
            </div>
          </>
        )}

        {!status?.can_apply && (
          <button onClick={onClose}
            className="w-full py-3 bg-dark-600 text-white font-semibold rounded-2xl">
            확인
          </button>
        )}
      </div>
    </div>
  );
};

export default BankruptcyModal;
