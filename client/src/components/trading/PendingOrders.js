// client/src/components/trading/PendingOrders.js
// =============================================================================
// 미체결 (대기) 주문 목록 컴포넌트
// =============================================================================
import React from 'react';
import { useFutures } from '../../contexts/FuturesContext';
import { useMarket } from '../../contexts/MarketContext';
import { formatPrice } from '../../utils/formatPrice';
import { toast } from 'react-toastify';

const PendingOrders = () => {
  const { positions, cancelPendingOrder } = useFutures();
  const { realtimePrices } = useMarket();
  
  // PENDING 상태 주문만 필터링
  const pendingOrders = positions.filter(
    (pos) => pos.status === 'PENDING'
  );

  const handleCancel = async (positionId) => {
    if (!window.confirm('이 대기 주문을 취소하시겠습니까?')) return;
    
    try {
      await cancelPendingOrder(positionId);
      toast.success('주문이 취소되었습니다');
    } catch (error) {
      toast.error('주문 취소 실패');
    }
  };

  if (pendingOrders.length === 0) {
    return null; // 대기 주문 없으면 표시 안 함
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold flex items-center">
          <span className="w-2 h-2 bg-yellow-400 rounded-full mr-2 animate-pulse" />
          대기 주문
          <span className="ml-2 px-2 py-0.5 bg-yellow-500 text-gray-900 text-sm rounded-full">
            {pendingOrders.length}
          </span>
        </h2>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-400 border-b border-gray-700">
              <th className="text-left py-3 px-2">종목</th>
              <th className="text-left py-3 px-2">방향</th>
              <th className="text-right py-3 px-2">지정가</th>
              <th className="text-right py-3 px-2">현재가</th>
              <th className="text-right py-3 px-2">수량</th>
              <th className="text-right py-3 px-2">레버리지</th>
              <th className="text-right py-3 px-2">증거금</th>
              <th className="text-center py-3 px-2">체결 조건</th>
              <th className="text-center py-3 px-2">작업</th>
            </tr>
          </thead>
          <tbody>
            {pendingOrders.map((order) => {
              const currentPrice = realtimePrices[order.symbol] || order.entry_price;
              const isLong = order.side === 'LONG';
              
              // 체결 가능 여부 확인
              // 롱: 현재가 <= 지정가면 체결 가능
              // 숏: 현재가 >= 지정가면 체결 가능
              const canFill = isLong 
                ? currentPrice <= order.entry_price
                : currentPrice >= order.entry_price;
              
              // 지정가까지 거리
              const priceDiff = isLong
                ? order.entry_price - currentPrice
                : currentPrice - order.entry_price;
              const priceDiffPercent = (priceDiff / currentPrice) * 100;

              return (
                <tr 
                  key={order.id} 
                  className="border-b border-gray-700 hover:bg-gray-700/50 transition-colors"
                >
                  <td className="py-3 px-2 font-semibold">
                    {order.symbol.replace('USDT', '')}
                  </td>
                  <td className="py-3 px-2">
                    <span className={`px-2 py-1 rounded text-xs font-bold ${
                      isLong ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                    }`}>
                      {isLong ? '📈 롱' : '📉 숏'}
                    </span>
                  </td>
                  <td className="py-3 px-2 text-right text-yellow-400 font-semibold">
                    ${formatPrice(order.entry_price)}
                  </td>
                  <td className="py-3 px-2 text-right">
                    ${formatPrice(currentPrice)}
                  </td>
                  <td className="py-3 px-2 text-right">
                    {parseFloat(order.quantity).toFixed(6)}
                  </td>
                  <td className="py-3 px-2 text-right text-yellow-400 font-semibold">
                    {order.leverage}x
                  </td>
                  <td className="py-3 px-2 text-right">
                    ${formatPrice(order.margin)}
                  </td>
                  <td className="py-3 px-2 text-center">
                    {canFill ? (
                      <span className="text-green-400 animate-pulse">
                        ✓ 체결 가능
                      </span>
                    ) : (
                      <span className="text-gray-400">
                        {isLong ? '↓' : '↑'} {priceDiffPercent.toFixed(2)}%
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-2 text-center">
                    <button
                      onClick={() => handleCancel(order.id)}
                      className="px-3 py-1 bg-gray-600 hover:bg-red-600 rounded text-sm font-semibold transition-colors"
                    >
                      취소
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* 안내 메시지 */}
      <div className="mt-4 p-3 bg-gray-700/50 rounded text-xs text-gray-400">
        <p>💡 <strong>지정가 주문 안내</strong></p>
        <ul className="mt-1 space-y-1 ml-4 list-disc">
          <li>롱: 현재가가 지정가 <strong>이하</strong>가 되면 체결</li>
          <li>숏: 현재가가 지정가 <strong>이상</strong>이 되면 체결</li>
          <li>더 유리한 가격에 체결될 수 있습니다</li>
        </ul>
      </div>
    </div>
  );
};

export default PendingOrders;