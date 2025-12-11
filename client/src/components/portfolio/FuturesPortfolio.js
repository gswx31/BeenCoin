// client/src/components/portfolio/FuturesPortfolio.js
// =============================================================================
// 포트폴리오에 손절/익절 편집 기능 통합
// =============================================================================

import React, { useState } from 'react';
import EditStopLossModal from './EditStopLossModal';
// ... 기존 imports ...

const FuturesPortfolio = () => {
  // ... 기존 states ...
  
  // 🆕 손절/익절 편집 모달
  const [editingPosition, setEditingPosition] = useState(null);

  // ... 기존 로직 ...

  // 🆕 손절/익절 편집 핸들러
  const handleEditStopLoss = (position) => {
    setEditingPosition(position);
  };

  // 🆕 손절/익절 업데이트 후
  const handleStopLossUpdated = (updatedPosition) => {
    // 포지션 목록 업데이트
    setPositions((prev) =>
      prev.map((pos) => (pos.id === updatedPosition.id ? updatedPosition : pos))
    );
    setEditingPosition(null);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {/* ... 기존 UI ... */}

      {/* 포지션 목록 */}
      <div className="space-y-4">
        {filteredPositions.map((position) => (
          <div key={position.id} className="bg-gray-800 rounded-lg p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-xl font-bold">{position.symbol}</h3>
                <span className={`text-sm ${
                  position.side === 'LONG' ? 'text-green-400' : 'text-red-400'
                }`}>
                  {position.side} {position.leverage}x
                </span>
              </div>

              {/* 🆕 버튼 그룹 */}
              <div className="flex space-x-2">
                {/* 손절/익절 편집 버튼 */}
                {position.status === 'OPEN' && (
                  <button
                    onClick={() => handleEditStopLoss(position)}
                    className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm"
                    title="손절/익절 설정"
                  >
                    📊 손절/익절
                  </button>
                )}

                {/* 청산 버튼 */}
                {position.status === 'OPEN' && (
                  <button
                    onClick={() => handleClosePosition(position.id)}
                    disabled={closingPositionId === position.id}
                    className="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-sm disabled:opacity-50"
                  >
                    {closingPositionId === position.id ? '청산 중...' : '청산'}
                  </button>
                )}
              </div>
            </div>

            {/* 포지션 정보 */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-400">진입가</span>
                <p className="font-semibold">${position.entry_price.toFixed(2)}</p>
              </div>
              <div>
                <span className="text-gray-400">현재가</span>
                <p className="font-semibold">${position.mark_price.toFixed(2)}</p>
              </div>
              <div>
                <span className="text-gray-400">미실현 손익</span>
                <p className={`font-semibold ${
                  position.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {position.unrealized_pnl >= 0 ? '+' : ''}${position.unrealized_pnl.toFixed(2)}
                  ({position.roe_percent >= 0 ? '+' : ''}{position.roe_percent.toFixed(2)}%)
                </p>
              </div>
              <div>
                <span className="text-gray-400">청산가</span>
                <p className="text-orange-400 font-semibold">
                  ${position.liquidation_price.toFixed(2)}
                </p>
              </div>
            </div>

            {/* 🆕 손절/익절 표시 */}
            {(position.stop_loss_price || position.take_profit_price) && (
              <div className="mt-4 pt-4 border-t border-gray-700">
                <div className="flex space-x-4 text-sm">
                  {position.stop_loss_price && (
                    <div>
                      <span className="text-gray-400">손절가: </span>
                      <span className="text-red-400 font-semibold">
                        ${position.stop_loss_price.toFixed(2)}
                      </span>
                    </div>
                  )}
                  {position.take_profit_price && (
                    <div>
                      <span className="text-gray-400">익절가: </span>
                      <span className="text-green-400 font-semibold">
                        ${position.take_profit_price.toFixed(2)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 🆕 손절/익절 편집 모달 */}
      {editingPosition && (
        <EditStopLossModal
          position={editingPosition}
          onClose={() => setEditingPosition(null)}
          onUpdate={handleStopLossUpdated}
        />
      )}
    </div>
  );
};

export default FuturesPortfolio;