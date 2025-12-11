// client/src/components/portfolio/EditStopLossModal.js
// =============================================================================
// 포지션 손절/익절 수정 모달
// =============================================================================
import React, { useState, useEffect } from 'react';
import axios from '../../api/axios';
import { endpoints } from '../../api/endpoints';
import { toast } from 'react-toastify';

const EditStopLossModal = ({ position, onClose, onUpdate }) => {
  const [stopLossEnabled, setStopLossEnabled] = useState(!!position.stop_loss_price);
  const [takeProfitEnabled, setTakeProfitEnabled] = useState(!!position.take_profit_price);
  const [stopLossPrice, setStopLossPrice] = useState(position.stop_loss_price || '');
  const [takeProfitPrice, setTakeProfitPrice] = useState(position.take_profit_price || '');
  const [loading, setLoading] = useState(false);

  // 현재가
  const currentPrice = position.mark_price;

  // 빠른 설정 버튼
  const handleQuickSet = (slPercent, tpPercent) => {
    const entryPrice = position.entry_price;
    
    if (position.side === 'LONG') {
      setStopLossPrice((entryPrice * (1 - slPercent / 100)).toFixed(2));
      setTakeProfitPrice((entryPrice * (1 + tpPercent / 100)).toFixed(2));
    } else {
      setStopLossPrice((entryPrice * (1 + slPercent / 100)).toFixed(2));
      setTakeProfitPrice((entryPrice * (1 - tpPercent / 100)).toFixed(2));
    }
    
    setStopLossEnabled(true);
    setTakeProfitEnabled(true);
  };

  // 저장
  const handleSave = async () => {
    try {
      setLoading(true);

      // 검증
      const entryPrice = position.entry_price;
      const slPrice = parseFloat(stopLossPrice);
      const tpPrice = parseFloat(takeProfitPrice);

      if (stopLossEnabled) {
        if (position.side === 'LONG' && slPrice >= entryPrice) {
          toast.error('롱 포지션의 손절가는 진입가보다 낮아야 합니다');
          return;
        }
        if (position.side === 'SHORT' && slPrice <= entryPrice) {
          toast.error('숏 포지션의 손절가는 진입가보다 높아야 합니다');
          return;
        }
      }

      if (takeProfitEnabled) {
        if (position.side === 'LONG' && tpPrice <= entryPrice) {
          toast.error('롱 포지션의 익절가는 진입가보다 높아야 합니다');
          return;
        }
        if (position.side === 'SHORT' && tpPrice >= entryPrice) {
          toast.error('숏 포지션의 익절가는 진입가보다 낮아야 합니다');
          return;
        }
      }

      // API 호출
      const response = await axios.patch(
        endpoints.futures.updateStopLoss(position.id),
        {
          stop_loss_price: stopLossEnabled ? stopLossPrice : null,
          take_profit_price: takeProfitEnabled ? takeProfitPrice : null,
        }
      );

      toast.success('손절/익절이 설정되었습니다');
      onUpdate(response.data);
      onClose();
    } catch (error) {
      console.error('손절/익절 설정 실패:', error);
      toast.error(error.response?.data?.detail || '설정 실패');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold">손절/익절 설정</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            ✕
          </button>
        </div>

        {/* 포지션 정보 */}
        <div className="bg-gray-700 rounded p-3 mb-4 text-sm">
          <div className="flex justify-between mb-1">
            <span className="text-gray-400">심볼:</span>
            <span className="font-semibold">{position.symbol}</span>
          </div>
          <div className="flex justify-between mb-1">
            <span className="text-gray-400">방향:</span>
            <span className={position.side === 'LONG' ? 'text-green-400' : 'text-red-400'}>
              {position.side}
            </span>
          </div>
          <div className="flex justify-between mb-1">
            <span className="text-gray-400">진입가:</span>
            <span>${position.entry_price.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">현재가:</span>
            <span>${currentPrice.toFixed(2)}</span>
          </div>
        </div>

        {/* 빠른 설정 */}
        <div className="mb-4">
          <label className="block text-sm text-gray-400 mb-2">빠른 설정</label>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => handleQuickSet(2, 4)}
              className="py-2 bg-gray-700 rounded hover:bg-gray-600 text-xs"
            >
              2% / 4%
            </button>
            <button
              type="button"
              onClick={() => handleQuickSet(3, 6)}
              className="py-2 bg-gray-700 rounded hover:bg-gray-600 text-xs"
            >
              3% / 6%
            </button>
            <button
              type="button"
              onClick={() => handleQuickSet(5, 10)}
              className="py-2 bg-gray-700 rounded hover:bg-gray-600 text-xs"
            >
              5% / 10%
            </button>
          </div>
        </div>

        {/* 손절 설정 */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm text-gray-400">손절 (Stop Loss)</label>
            <input
              type="checkbox"
              checked={stopLossEnabled}
              onChange={(e) => setStopLossEnabled(e.target.checked)}
              className="w-4 h-4"
            />
          </div>
          {stopLossEnabled && (
            <input
              type="number"
              step="0.01"
              value={stopLossPrice}
              onChange={(e) => setStopLossPrice(e.target.value)}
              placeholder="손절 가격"
              className="w-full px-4 py-2 bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
            />
          )}
        </div>

        {/* 익절 설정 */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm text-gray-400">익절 (Take Profit)</label>
            <input
              type="checkbox"
              checked={takeProfitEnabled}
              onChange={(e) => setTakeProfitEnabled(e.target.checked)}
              className="w-4 h-4"
            />
          </div>
          {takeProfitEnabled && (
            <input
              type="number"
              step="0.01"
              value={takeProfitPrice}
              onChange={(e) => setTakeProfitPrice(e.target.value)}
              placeholder="익절 가격"
              className="w-full px-4 py-2 bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          )}
        </div>

        {/* 버튼 */}
        <div className="flex space-x-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-2 bg-gray-700 rounded hover:bg-gray-600"
          >
            취소
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={loading}
            className="flex-1 py-2 bg-accent text-dark rounded hover:bg-accent-hover font-semibold disabled:opacity-50"
          >
            {loading ? '저장 중...' : '저장'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default EditStopLossModal;