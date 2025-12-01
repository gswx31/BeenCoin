// client/src/components/trading/PositionsList.js
// =============================================================================
// 포지션 리스트 컴포넌트 - 모든 활성 포지션 표시
// =============================================================================
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useFutures } from '../../contexts/FuturesContext';
import { useMarket } from '../../contexts/MarketContext';
import { formatPrice } from '../../utils/formatPrice';

const PositionsList = () => {
  const navigate = useNavigate();
  const { positions, positionsLoading, closePosition } = useFutures();
  const { realtimePrices } = useMarket();
  const [closingId, setClosingId] = useState(null);

  // 활성 포지션만 필터링
  const openPositions = positions.filter((pos) => pos.status === 'OPEN');

  const handleClose = async (positionId) => {
    if (closingId) return;

    const confirmed = window.confirm('포지션을 청산하시겠습니까?');
    if (!confirmed) return;

    setClosingId(positionId);
    await closePosition(positionId);
    setClosingId(null);
  };

  if (positionsLoading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">활성 포지션</h2>
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
        </div>
      </div>
    );
  }

  if (openPositions.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">활성 포지션</h2>
        <div className="text-center py-8 text-gray-400">
          <p>활성 포지션이 없습니다</p>
          <p className="text-sm mt-2">위에서 포지션을 개설해보세요</p>
        </div>
      </div>
    );
  }

  // 총 미실현 손익 계산
  const totalUnrealizedPnl = openPositions.reduce((sum, pos) => {
    const currentPrice = realtimePrices[pos.symbol] || pos.mark_price;
    let pnl;
    if (pos.side === 'LONG') {
      pnl = (currentPrice - pos.entry_price) * pos.quantity;
    } else {
      pnl = (pos.entry_price - currentPrice) * pos.quantity;
    }
    return sum + pnl;
  }, 0);

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">
          활성 포지션 ({openPositions.length})
        </h2>
        <div className={`text-lg font-bold ${totalUnrealizedPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          총 손익: {totalUnrealizedPnl >= 0 ? '+' : ''}${formatPrice(totalUnrealizedPnl)}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-gray-400 text-sm border-b border-gray-700">
              <th className="text-left py-3 px-2">심볼</th>
              <th className="text-left py-3 px-2">방향</th>
              <th className="text-right py-3 px-2">수량</th>
              <th className="text-right py-3 px-2">레버리지</th>
              <th className="text-right py-3 px-2">진입가</th>
              <th className="text-right py-3 px-2">현재가</th>
              <th className="text-right py-3 px-2">청산가</th>
              <th className="text-right py-3 px-2">미실현 손익</th>
              <th className="text-right py-3 px-2">ROE</th>
              <th className="text-center py-3 px-2">액션</th>
            </tr>
          </thead>
          <tbody>
            {openPositions.map((pos) => {
              const currentPrice = realtimePrices[pos.symbol] || pos.mark_price || 0;
              
              // 실시간 PnL 계산
              let unrealizedPnl;
              if (pos.side === 'LONG') {
                unrealizedPnl = (currentPrice - pos.entry_price) * pos.quantity;
              } else {
                unrealizedPnl = (pos.entry_price - currentPrice) * pos.quantity;
              }
              
              const roe = pos.margin > 0 ? (unrealizedPnl / pos.margin) * 100 : 0;
              const pnlColor = unrealizedPnl >= 0 ? 'text-green-400' : 'text-red-400';
              const sideColor = pos.side === 'LONG' ? 'text-green-400' : 'text-red-400';
              const sideBg = pos.side === 'LONG' ? 'bg-green-600' : 'bg-red-600';

              return (
                <tr
                  key={pos.id}
                  className="border-b border-gray-700 hover:bg-gray-750 transition-colors"
                >
                  <td className="py-3 px-2">
                    <button
                      onClick={() => navigate(`/futures/${pos.symbol}`)}
                      className="font-semibold hover:text-accent transition-colors"
                    >
                      {pos.symbol.replace('USDT', '')}
                    </button>
                  </td>
                  <td className="py-3 px-2">
                    <span className={`px-2 py-1 ${sideBg} rounded text-xs font-bold`}>
                      {pos.side === 'LONG' ? '📈 롱' : '📉 숏'}
                    </span>
                  </td>
                  <td className="py-3 px-2 text-right">
                    {parseFloat(pos.quantity).toFixed(6)}
                  </td>
                  <td className="py-3 px-2 text-right text-yellow-400 font-semibold">
                    {pos.leverage}x
                  </td>
                  <td className="py-3 px-2 text-right">
                    ${formatPrice(pos.entry_price)}
                  </td>
                  <td className="py-3 px-2 text-right">
                    ${formatPrice(currentPrice)}
                  </td>
                  <td className="py-3 px-2 text-right text-orange-400">
                    ${formatPrice(pos.liquidation_price)}
                  </td>
                  <td className={`py-3 px-2 text-right font-semibold ${pnlColor}`}>
                    {unrealizedPnl >= 0 ? '+' : ''}${formatPrice(unrealizedPnl)}
                  </td>
                  <td className={`py-3 px-2 text-right font-bold ${pnlColor}`}>
                    {roe >= 0 ? '+' : ''}{roe.toFixed(2)}%
                  </td>
                  <td className="py-3 px-2 text-center">
                    <button
                      onClick={() => handleClose(pos.id)}
                      disabled={closingId === pos.id}
                      className="px-3 py-1 bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-sm font-semibold transition-colors"
                    >
                      {closingId === pos.id ? '...' : '청산'}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* 범례 */}
      <div className="mt-4 flex flex-wrap gap-4 text-xs text-gray-400">
        <span>📈 롱: 가격 상승 시 이익</span>
        <span>📉 숏: 가격 하락 시 이익</span>
        <span className="text-orange-400">청산가: 강제 청산 가격</span>
        <span className="text-yellow-400">레버리지: 증거금 대비 포지션 배율</span>
      </div>
    </div>
  );
};

export default PositionsList;