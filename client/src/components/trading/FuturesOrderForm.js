// client/src/components/trading/FuturesOrderForm.js
// =============================================================================
// 선물 거래 주문 폼 - 백엔드 API 완벽 연동
// =============================================================================
import React, { useState, useEffect, useCallback } from 'react';
import { useFutures } from '../../contexts/FuturesContext';
import { useMarket } from '../../contexts/MarketContext';
import { formatPrice } from '../../utils/formatPrice';
import { toast } from 'react-toastify';

const FuturesOrderForm = ({ symbol, currentPrice }) => {
  const { account, openPosition, fetchAccount } = useFutures();
  const { getPrice } = useMarket();

  // 주문 상태
  const [side, setSide] = useState('LONG');
  const [orderType, setOrderType] = useState('MARKET');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [leverage, setLeverage] = useState(10);
  const [loading, setLoading] = useState(false);

  // 계산된 값
  const [calculations, setCalculations] = useState({
    positionValue: 0,
    requiredMargin: 0,
    estimatedFee: 0,
    liquidationPrice: 0,
    totalCost: 0,
  });

  // 현재가 업데이트
  const realPrice = getPrice(symbol) || currentPrice;

  // ===========================================
  // 계산 로직
  // ===========================================
  const calculateOrder = useCallback(() => {
    const qty = parseFloat(quantity) || 0;
    const orderPrice = orderType === 'MARKET' ? realPrice : (parseFloat(price) || realPrice);
    const lev = leverage;

    if (qty <= 0 || orderPrice <= 0) {
      setCalculations({
        positionValue: 0,
        requiredMargin: 0,
        estimatedFee: 0,
        liquidationPrice: 0,
        totalCost: 0,
      });
      return;
    }

    // 실제 포지션 크기 (레버리지 적용)
    const actualQuantity = qty * lev;
    
    // 포지션 가치
    const positionValue = actualQuantity * orderPrice;
    
    // 필요 증거금
    const requiredMargin = positionValue / lev;
    
    // 수수료 (0.04%)
    const feeRate = 0.0004;
    const estimatedFee = positionValue * feeRate;
    
    // 총 필요 금액
    const totalCost = requiredMargin + estimatedFee;
    
    // 청산가 계산 (증거금의 90% 손실 시)
    const liquidationMargin = requiredMargin * 0.9;
    let liquidationPrice;
    if (side === 'LONG') {
      liquidationPrice = orderPrice - (liquidationMargin / actualQuantity);
    } else {
      liquidationPrice = orderPrice + (liquidationMargin / actualQuantity);
    }

    setCalculations({
      positionValue,
      requiredMargin,
      estimatedFee,
      liquidationPrice: Math.max(0, liquidationPrice),
      totalCost,
    });
  }, [quantity, price, orderType, leverage, side, realPrice]);

  useEffect(() => {
    calculateOrder();
  }, [calculateOrder]);

  // 지정가 주문 시 현재가로 초기화
  useEffect(() => {
    if (orderType === 'LIMIT' && !price && realPrice > 0) {
      setPrice(realPrice.toString());
    }
  }, [orderType, realPrice]);

  // ===========================================
  // 퍼센트 버튼 핸들러
  // ===========================================
  const handlePercentageClick = (percent) => {
    if (!account?.available_balance) {
      toast.warning('잔액을 확인할 수 없습니다.');
      return;
    }

    const availableBalance = parseFloat(account.available_balance);
    const orderPrice = orderType === 'MARKET' ? realPrice : (parseFloat(price) || realPrice);
    
    if (orderPrice <= 0) {
      toast.warning('가격을 확인해주세요.');
      return;
    }

    // 사용할 증거금 금액
    const marginToUse = availableBalance * (percent / 100);
    
    // 수수료를 고려한 증거금
    const feeRate = 0.0004;
    const effectiveMargin = marginToUse / (1 + feeRate);
    
    // 계약 수량 계산 (레버리지 적용 전)
    // positionValue = quantity * leverage * price
    // requiredMargin = positionValue / leverage = quantity * price
    // quantity = requiredMargin / price
    const calculatedQty = effectiveMargin / orderPrice;

    if (calculatedQty > 0) {
      setQuantity(calculatedQty.toFixed(8));
    }
  };

  // ===========================================
  // 레버리지 조절
  // ===========================================
  const handleLeverageChange = (newLeverage) => {
    const clampedLeverage = Math.max(1, Math.min(125, newLeverage));
    setLeverage(clampedLeverage);
  };

  // ===========================================
  // 주문 제출
  // ===========================================
  const handleSubmit = async (e) => {
    e.preventDefault();

    const qty = parseFloat(quantity);
    if (!qty || qty <= 0) {
      toast.error('수량을 입력해주세요.');
      return;
    }

    if (orderType === 'LIMIT') {
      const limitPrice = parseFloat(price);
      if (!limitPrice || limitPrice <= 0) {
        toast.error('가격을 입력해주세요.');
        return;
      }
    }

    // 잔액 확인
    if (account && calculations.totalCost > parseFloat(account.available_balance)) {
      toast.error(
        `증거금이 부족합니다.\n` +
        `필요: $${calculations.totalCost.toFixed(2)}\n` +
        `보유: $${parseFloat(account.available_balance).toFixed(2)}`
      );
      return;
    }

    setLoading(true);

    const orderData = {
      symbol,
      side,
      quantity: qty,
      leverage,
      orderType,
      price: orderType === 'LIMIT' ? parseFloat(price) : undefined,
    };

    const result = await openPosition(orderData);

    if (result.success) {
      // 폼 초기화
      setQuantity('');
      setPrice('');
      await fetchAccount();
    }

    setLoading(false);
  };

  // ===========================================
  // 렌더링
  // ===========================================
  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h2 className="text-xl font-bold mb-6">선물 주문</h2>

      {/* 주문 타입 선택 */}
      <div className="flex space-x-2 mb-4">
        <button
          onClick={() => setOrderType('MARKET')}
          className={`flex-1 py-2 rounded-lg transition-colors ${
            orderType === 'MARKET'
              ? 'bg-accent text-white'
              : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
          }`}
        >
          시장가
        </button>
        <button
          onClick={() => setOrderType('LIMIT')}
          className={`flex-1 py-2 rounded-lg transition-colors ${
            orderType === 'LIMIT'
              ? 'bg-accent text-white'
              : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
          }`}
        >
          지정가
        </button>
      </div>

      {/* 롱/숏 선택 */}
      <div className="flex space-x-2 mb-6">
        <button
          onClick={() => setSide('LONG')}
          className={`flex-1 py-3 rounded-lg font-semibold transition-colors ${
            side === 'LONG'
              ? 'bg-green-600 text-white'
              : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
          }`}
        >
          📈 롱 (매수)
        </button>
        <button
          onClick={() => setSide('SHORT')}
          className={`flex-1 py-3 rounded-lg font-semibold transition-colors ${
            side === 'SHORT'
              ? 'bg-red-600 text-white'
              : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
          }`}
        >
          📉 숏 (매도)
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* 레버리지 슬라이더 */}
        <div>
          <label className="block text-sm text-gray-400 mb-2">
            레버리지: <span className="text-yellow-400 font-bold">{leverage}x</span>
          </label>
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={() => handleLeverageChange(leverage - 1)}
              className="px-3 py-2 bg-gray-700 rounded hover:bg-gray-600"
            >
              -
            </button>
            <input
              type="range"
              min="1"
              max="125"
              value={leverage}
              onChange={(e) => handleLeverageChange(parseInt(e.target.value))}
              className="flex-1 accent-accent"
            />
            <button
              type="button"
              onClick={() => handleLeverageChange(leverage + 1)}
              className="px-3 py-2 bg-gray-700 rounded hover:bg-gray-600"
            >
              +
            </button>
          </div>
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>1x</span>
            <span>25x</span>
            <span>50x</span>
            <span>75x</span>
            <span>100x</span>
            <span>125x</span>
          </div>
        </div>

        {/* 지정가 입력 */}
        {orderType === 'LIMIT' && (
          <div>
            <label className="block text-sm text-gray-400 mb-2">주문 가격 (USDT)</label>
            <input
              type="number"
              step="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              className="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent"
              placeholder="주문 가격"
            />
          </div>
        )}

        {/* 수량 입력 */}
        <div>
          <label className="block text-sm text-gray-400 mb-2">
            수량 ({symbol.replace('USDT', '')})
          </label>
          <input
            type="number"
            step="0.00000001"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent"
            placeholder="주문 수량"
          />
        </div>

        {/* 퍼센트 버튼 */}
        <div>
          <label className="block text-sm text-gray-400 mb-2">증거금 비율</label>
          <div className="grid grid-cols-4 gap-2">
            {[25, 50, 75, 100].map((percent) => (
              <button
                key={percent}
                type="button"
                onClick={() => handlePercentageClick(percent)}
                className="py-2 rounded-lg bg-gray-700 text-gray-400 hover:bg-gray-600 transition-colors"
              >
                {percent}%
              </button>
            ))}
          </div>
        </div>

        {/* 주문 정보 */}
        <div className="bg-gray-700 rounded-lg p-4 space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">사용 가능</span>
            <span className="font-semibold">
              ${account ? formatPrice(account.available_balance) : '---'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">포지션 가치</span>
            <span className="font-semibold">
              ${formatPrice(calculations.positionValue)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">필요 증거금</span>
            <span className="font-semibold text-yellow-400">
              ${formatPrice(calculations.requiredMargin)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">예상 수수료 (0.04%)</span>
            <span className="text-gray-300">
              ${formatPrice(calculations.estimatedFee)}
            </span>
          </div>
          <div className="border-t border-gray-600 pt-2 flex justify-between">
            <span className="text-gray-400">총 필요 금액</span>
            <span className="font-bold text-accent">
              ${formatPrice(calculations.totalCost)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">예상 청산가</span>
            <span className={`font-semibold ${side === 'LONG' ? 'text-red-400' : 'text-green-400'}`}>
              ${formatPrice(calculations.liquidationPrice)}
            </span>
          </div>
        </div>

        {/* 경고 메시지 */}
        {leverage >= 50 && (
          <div className="bg-red-900 bg-opacity-30 border border-red-700 rounded-lg p-3 text-sm text-red-300">
            ⚠️ 고레버리지 주의: {leverage}x 레버리지는 높은 위험을 수반합니다.
            작은 가격 변동에도 청산될 수 있습니다.
          </div>
        )}

        {/* 제출 버튼 */}
        <button
          type="submit"
          disabled={loading || !quantity}
          className={`w-full py-3 rounded-lg font-bold text-white transition-colors ${
            side === 'LONG'
              ? 'bg-green-600 hover:bg-green-700'
              : 'bg-red-600 hover:bg-red-700'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {loading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              처리 중...
            </span>
          ) : (
            `${side === 'LONG' ? '롱' : '숏'} 포지션 개설 (${leverage}x)`
          )}
        </button>
      </form>

      {/* 추가 정보 */}
      <div className="mt-4 text-xs text-gray-500 space-y-1">
        <p>• 시장가 주문은 현재가({formatPrice(realPrice)} USDT)로 즉시 체결됩니다</p>
        <p>• 지정가 주문은 목표가 도달 시 체결됩니다</p>
        <p>• 청산가에 도달하면 포지션이 강제 청산됩니다</p>
      </div>
    </div>
  );
};

export default FuturesOrderForm;