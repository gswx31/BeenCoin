// client/src/components/common/PriceAlert.js
// =============================================================================
// 가격 알림 컴포넌트 - 실제 거래소 기능
// =============================================================================
import React, { useState, useEffect, useCallback } from 'react';
import { useMarket } from '../../contexts/MarketContext';
import { useAuth } from '../../contexts/AuthContext';
import axios from '../../api/axios';
import { endpoints } from '../../api/endpoints';
import { toast } from 'react-toastify';
import { formatPrice } from '../../utils/formatPrice';

const PriceAlert = ({ symbol, onClose }) => {
  const { isAuthenticated } = useAuth();
  const { realtimePrices } = useMarket();
  
  const currentPrice = realtimePrices[symbol] || 0;
  
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // 새 알림 폼
  const [targetPrice, setTargetPrice] = useState('');
  const [condition, setCondition] = useState('>='); // >= 또는 <=
  const [note, setNote] = useState('');
  const [creating, setCreating] = useState(false);

  // =========================================================================
  // 알림 목록 로드
  // =========================================================================
  const fetchAlerts = useCallback(async () => {
    if (!isAuthenticated) return;
    
    try {
      const response = await axios.get(endpoints.stopOrders.alerts, {
        params: { symbol }
      });
      setAlerts(response.data || []);
    } catch (error) {
      console.error('알림 목록 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, symbol]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  // =========================================================================
  // 알림 생성
  // =========================================================================
  const handleCreate = async (e) => {
    e.preventDefault();
    
    if (!targetPrice) {
      toast.error('목표 가격을 입력해주세요');
      return;
    }
    
    setCreating(true);
    
    try {
      await axios.post(endpoints.stopOrders.alerts, {
        symbol,
        target_price: parseFloat(targetPrice),
        condition,
        note: note || null,
      });
      
      toast.success('가격 알림이 설정되었습니다');
      setTargetPrice('');
      setNote('');
      fetchAlerts();
    } catch (error) {
      toast.error('알림 설정에 실패했습니다');
    } finally {
      setCreating(false);
    }
  };

  // =========================================================================
  // 알림 삭제
  // =========================================================================
  const handleDelete = async (alertId) => {
    try {
      await axios.delete(`${endpoints.stopOrders.alerts}/${alertId}`);
      toast.success('알림이 삭제되었습니다');
      fetchAlerts();
    } catch (error) {
      toast.error('알림 삭제에 실패했습니다');
    }
  };

  // =========================================================================
  // 퍼센트 버튼으로 가격 설정
  // =========================================================================
  const setPercentPrice = (percent, direction) => {
    if (currentPrice <= 0) return;
    
    const multiplier = direction === 'up' 
      ? 1 + percent / 100 
      : 1 - percent / 100;
    
    setTargetPrice((currentPrice * multiplier).toFixed(2));
    setCondition(direction === 'up' ? '>=' : '<=');
  };

  // =========================================================================
  // 렌더링
  // =========================================================================
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">🔔 가격 알림</h3>
        {onClose && (
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            ✕
          </button>
        )}
      </div>

      {/* 현재가 표시 */}
      <div className="mb-4 p-3 bg-gray-700 rounded">
        <span className="text-gray-400 text-sm">현재가</span>
        <p className="text-xl font-bold text-white">{formatPrice(currentPrice)}</p>
      </div>

      {/* 알림 생성 폼 */}
      <form onSubmit={handleCreate} className="space-y-3 mb-6">
        {/* 퍼센트 버튼 */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className="text-xs text-gray-400 mb-1 block">상승 알림</span>
            <div className="flex gap-1">
              {[1, 3, 5, 10].map(pct => (
                <button
                  key={`up-${pct}`}
                  type="button"
                  onClick={() => setPercentPrice(pct, 'up')}
                  className="flex-1 py-1 text-xs bg-green-900/50 text-green-400 rounded hover:bg-green-800/50"
                >
                  +{pct}%
                </button>
              ))}
            </div>
          </div>
          <div>
            <span className="text-xs text-gray-400 mb-1 block">하락 알림</span>
            <div className="flex gap-1">
              {[1, 3, 5, 10].map(pct => (
                <button
                  key={`down-${pct}`}
                  type="button"
                  onClick={() => setPercentPrice(pct, 'down')}
                  className="flex-1 py-1 text-xs bg-red-900/50 text-red-400 rounded hover:bg-red-800/50"
                >
                  -{pct}%
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* 가격 입력 */}
        <div className="flex gap-2">
          <select
            value={condition}
            onChange={(e) => setCondition(e.target.value)}
            className="bg-gray-700 text-white rounded px-3 py-2"
          >
            <option value=">=">≥ 이상</option>
            <option value="<=">≤ 이하</option>
          </select>
          <input
            type="number"
            value={targetPrice}
            onChange={(e) => setTargetPrice(e.target.value)}
            placeholder="목표 가격"
            step="0.01"
            className="flex-1 bg-gray-700 text-white rounded px-3 py-2"
          />
        </div>

        {/* 메모 */}
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="메모 (선택사항)"
          maxLength={100}
          className="w-full bg-gray-700 text-white rounded px-3 py-2"
        />

        {/* 생성 버튼 */}
        <button
          type="submit"
          disabled={creating || !targetPrice}
          className="w-full py-2 bg-blue-600 text-white rounded hover:bg-blue-500 disabled:opacity-50"
        >
          {creating ? '설정 중...' : '알림 설정'}
        </button>
      </form>

      {/* 설정된 알림 목록 */}
      <div>
        <h4 className="text-sm text-gray-400 mb-2">설정된 알림</h4>
        
        {loading ? (
          <div className="text-center py-4 text-gray-500">로딩 중...</div>
        ) : alerts.length === 0 ? (
          <div className="text-center py-4 text-gray-500">설정된 알림이 없습니다</div>
        ) : (
          <div className="space-y-2 max-h-[200px] overflow-y-auto">
            {alerts.map(alert => (
              <div 
                key={alert.id}
                className={`flex items-center justify-between p-2 rounded ${
                  alert.is_active ? 'bg-gray-700' : 'bg-gray-700/50 opacity-60'
                }`}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-mono ${
                      alert.condition === '>=' ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {alert.condition} {formatPrice(parseFloat(alert.target_price))}
                    </span>
                    {alert.triggered_at && (
                      <span className="text-xs bg-yellow-600 text-white px-1 rounded">
                        발동됨
                      </span>
                    )}
                  </div>
                  {alert.note && (
                    <p className="text-xs text-gray-400 mt-0.5">{alert.note}</p>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(alert.id)}
                  className="text-gray-400 hover:text-red-400 p-1"
                >
                  🗑
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PriceAlert;