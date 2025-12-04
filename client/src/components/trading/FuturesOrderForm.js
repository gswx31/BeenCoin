// client/src/components/trading/FuturesOrderForm.js
// =============================================================================
// 선물 주문 폼 - 100% 주문 시 수수료 선차감
// =============================================================================
import React, { useState, useEffect, useCallback } from 'react';
import { useFutures } from '../../contexts/FuturesContext';
import { useMarket } from '../../contexts/MarketContext';
import { formatPrice } from '../../utils/formatPrice';
import { toast } from 'react-toastify';

const FEE_RATE = 0.0004; // 0.04%

const FuturesOrderForm = ({ symbol, currentPrice }) => {
  const { account, openPosition, fetchAccount } = useFutures();
  const { realtimePrices } = useMarket();

  const [side, setSide] = useState('LONG');
  const [orderType, setOrderType] = useState('MARKET');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [leverage, setLeverage] = useState(10);
  const [loading, setLoading] = useState(false);
  const [calculations, setCalculations] = useState({
    positionValue: 0,
    requiredMargin: 0,
    estimatedFee: 0,
    liquidationPrice: 0,
    totalCost: 0,
  });

  const realPrice = realtimePrices[symbol] || currentPrice || 0;

  // ===========================================
  // ⭐ 수정: 최대 주문 가능 수량 계산 (수수료 포함)
  // ===========================================
  const calculateMaxQuantity = useCallback(() => {
    if (!account?.available_balance || realPrice <= 0) return 0;
    
    const availableBalance = parseFloat(account.available_balance);
    const orderPrice = orderType === 'MARKET' ? realPrice : (parseFloat(price) || realPrice);
    
    if (orderPrice <= 0) return 0;
    
    // ⭐ 핵심: 수수료를 고려한 최대 수량 계산
    // 총 필요 = 수량 × 가격 × (1 + 레버리지 × 수수료율)
    // 최대 수량 = 잔액 / (가격 × (1 + 레버리지 × 수수료율))
    const feeMultiplier = 1 + (leverage * FEE_RATE);
    const maxQuantity = availableBalance / (orderPrice * feeMultiplier);
    
    return maxQuantity;
  }, [account, realPrice, orderType, price, leverage]);

  // ===========================================
  // 주문 계산
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
    const estimatedFee = positionValue * FEE_RATE;
    
    // 총 필요 금액
    const totalCost = requiredMargin + estimatedFee;
    
    // 청산가 계산
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
      setPrice(realPrice.toFixed(2));
    }
  }, [orderType, realPrice, price]);

  // ===========================================
  // ⭐ 수정: 퍼센트 버튼 핸들러 (수수료 포함)
  // ===========================================
  const handlePercentageClick = (percent) => {
    if (!account?.available_balance) {
      toast.warning('잔액을 확인할 수 없습니다.');
      return;
    }

    const maxQty = calculateMaxQuantity();
    
    if (maxQty <= 0) {
      toast.warning('가격을 확인해주세요.');
      return;
    }
    
    // 퍼센트에 따른 수량 계산
    const targetQty = maxQty * (percent / 100);
    
    // 소수점 6자리로 반올림
    const roundedQty = Math.floor(targetQty * 1000000) / 1000000;
    
    setQuantity(roundedQty.toString());
    
    if (percent === 100) {
      toast.info(`100% 주문 (수수료 ${(leverage * FEE_RATE * 100).toFixed(3)}% 포함)`);
    }
  };

  // ===========================================
  // 레버리지 슬라이더
  // ===========================================
  const leverageMarks = [1, 5, 10, 25, 50, 75, 100, 125];

  const handleLeverageChange = (e) => {
    setLeverage(parseInt(e.target.value));
  };

  // ===========================================
  // 주문 제출
  // ===========================================
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!quantity || parseFloat(quantity) <= 0) {
      toast.error('수량을 입력해주세요.');
      return;
    }

    if (orderType === 'LIMIT' && (!price || parseFloat(price) <= 0)) {
      toast.error('지정가를 입력해주세요.');
      return;
    }

    // 잔액 확인
    if (calculations.totalCost > parseFloat(account?.available_balance || 0)) {
      toast.error(`잔액 부족: 필요 ${formatPrice(calculations.totalCost)} USDT`);
      return;
    }

    setLoading(true);

    try {
      const orderData = {
        symbol,
        side,
        quantity: parseFloat(quantity),
        leverage,
        order_type: orderType,
        price: orderType === 'LIMIT' ? parseFloat(price) : null,
      };

      await openPosition(orderData);
      
      // 성공 후 초기화
      setQuantity('');
      if (orderType === 'LIMIT') {
        setPrice('');
      }
      
      // 계정 정보 새로고침
      await fetchAccount();
      
    } catch (error) {
      // 에러는 openPosition에서 toast로 처리됨
      console.error('주문 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  // 잔액 대비 사용 비율
  const usagePercent = account?.available_balance > 0 
    ? (calculations.totalCost / parseFloat(account.available_balance)) * 100 
    : 0;

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4">선물 주문</h2>

      {/* 계정 정보 */}
      <div className="bg-gray-700 rounded-lg p-4 mb-4">
        <div className="flex justify-between text-sm mb-2">
          <span className="text-gray-400">사용 가능</span>
          <span className="text-white font-semibold">
            {formatPrice(account?.available_balance || 0)} USDT
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">사용 중</span>
          <span className="text-yellow-400">
            {formatPrice(account?.margin_used || 0)} USDT
          </span>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* 롱/숏 선택 */}
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => setSide('LONG')}
            className={`py-3 rounded-lg font-semibold transition-all ${
              side === 'LONG'
                ? 'bg-green-600 text-white shadow-lg shadow-green-600/30'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
          >
            📈 롱 (매수)
          </button>
          <button
            type="button"
            onClick={() => setSide('SHORT')}
            className={`py-3 rounded-lg font-semibold transition-all ${
              side === 'SHORT'
                ? 'bg-red-600 text-white shadow-lg shadow-red-600/30'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
          >
            📉 숏 (매도)
          </button>
        </div>

        {/* 주문 유형 */}
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => setOrderType('MARKET')}
            className={`py-2 rounded text-sm font-medium transition-all ${
              orderType === 'MARKET'
                ? 'bg-teal-600 text-white'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
          >
            시장가
          </button>
          <button
            type="button"
            onClick={() => setOrderType('LIMIT')}
            className={`py-2 rounded text-sm font-medium transition-all ${
              orderType === 'LIMIT'
                ? 'bg-teal-600 text-white'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
          >
            지정가
          </button>
        </div>

        {/* 지정가 입력 */}
        {orderType === 'LIMIT' && (
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              지정가 (USDT)
            </label>
            <div className="relative">
              <input
                type="number"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                placeholder="0.00"
                step="0.01"
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
              <button
                type="button"
                onClick={() => setPrice(realPrice.toFixed(2))}
                className="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 text-xs bg-gray-600 hover:bg-gray-500 rounded"
              >
                현재가
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {side === 'LONG' ? '지정가 이하' : '지정가 이상'}에서 체결됩니다
            </p>
          </div>
        )}

        {/* 레버리지 */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm text-gray-400">레버리지</label>
            <span className="text-lg font-bold text-yellow-400">{leverage}x</span>
          </div>
          <input
            type="range"
            min="1"
            max="125"
            value={leverage}
            onChange={handleLeverageChange}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-yellow-500"
          />
          <div className="flex justify-between mt-2">
            {leverageMarks.map((mark) => (
              <button
                key={mark}
                type="button"
                onClick={() => setLeverage(mark)}
                className={`px-2 py-1 text-xs rounded transition-all ${
                  leverage === mark
                    ? 'bg-yellow-500 text-gray-900 font-bold'
                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                }`}
              >
                {mark}x
              </button>
            ))}
          </div>
        </div>

        {/* 수량 */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">
            수량 ({symbol.replace('USDT', '')})
          </label>
          <input
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="0.000000"
            step="0.000001"
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
          
          {/* ⭐ 퍼센트 버튼 */}
          <div className="grid grid-cols-4 gap-2 mt-2">
            {[25, 50, 75, 100].map((percent) => (
              <button
                key={percent}
                type="button"
                onClick={() => handlePercentageClick(percent)}
                className="py-2 text-sm bg-gray-700 hover:bg-gray-600 rounded font-medium transition-colors"
              >
                {percent}%
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-1">
            최대: {formatPrice(calculateMaxQuantity())} {symbol.replace('USDT', '')}
          </p>
        </div>

        {/* 주문 요약 */}
        <div className="bg-gray-700 rounded-lg p-4 space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">포지션 가치</span>
            <span>${formatPrice(calculations.positionValue)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">필요 증거금</span>
            <span>{formatPrice(calculations.requiredMargin)} USDT</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">예상 수수료 (0.04%)</span>
            <span className="text-yellow-400">{formatPrice(calculations.estimatedFee)} USDT</span>
          </div>
          <hr className="border-gray-600" />
          <div className="flex justify-between font-semibold">
            <span className="text-gray-400">총 필요 금액</span>
            <span className={usagePercent > 100 ? 'text-red-400' : 'text-white'}>
              {formatPrice(calculations.totalCost)} USDT
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">예상 청산가</span>
            <span className="text-orange-400">${formatPrice(calculations.liquidationPrice)}</span>
          </div>
          
          {/* 잔액 사용률 바 */}
          <div className="mt-2">
            <div className="h-2 bg-gray-600 rounded-full overflow-hidden">
              <div 
                className={`h-full transition-all ${
                  usagePercent > 100 ? 'bg-red-500' : 
                  usagePercent > 80 ? 'bg-yellow-500' : 'bg-teal-500'
                }`}
                style={{ width: `${Math.min(usagePercent, 100)}%` }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1 text-right">
              잔액의 {usagePercent.toFixed(1)}% 사용
            </p>
          </div>
        </div>

        {/* 제출 버튼 */}
        <button
          type="submit"
          disabled={loading || !quantity || calculations.totalCost > parseFloat(account?.available_balance || 0)}
          className={`w-full py-4 rounded-lg font-bold text-lg transition-all ${
            side === 'LONG'
              ? 'bg-green-600 hover:bg-green-700 disabled:bg-green-800'
              : 'bg-red-600 hover:bg-red-700 disabled:bg-red-800'
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
            <>
              {side === 'LONG' ? '📈 롱 포지션 열기' : '📉 숏 포지션 열기'}
              {orderType === 'LIMIT' && ' (지정가)'}
            </>
          )}
        </button>

        {/* 경고 메시지 */}
        {leverage >= 50 && (
          <p className="text-xs text-orange-400 text-center">
            ⚠️ 고레버리지 거래는 높은 위험을 수반합니다
          </p>
        )}
      </form>
    </div>
  );
};

export default FuturesOrderForm;