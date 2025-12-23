// client/src/components/trading/FuturesOrderForm.js
// =============================================================================
// 선물 주문 폼 - 바이낸스 스타일 (스탑 제거)
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
  const [quantityMode, setQuantityMode] = useState('quantity');
  const [quantity, setQuantity] = useState('');
  const [amount, setAmount] = useState('');
  const [percentage, setPercentage] = useState(100);
  const [price, setPrice] = useState('');
  const [leverage, setLeverage] = useState(10);
  
  const [loading, setLoading] = useState(false);
  const [calculations, setCalculations] = useState({
    positionValue: 0,
    requiredMargin: 0,
    estimatedFee: 0,
    liquidationPrice: 0,
    totalCost: 0,
    actualQuantity: 0,
  });

  const realPrice = realtimePrices[symbol] || currentPrice || 0;

  // 초기화
  useEffect(() => {
    if (realPrice > 0 && orderType === 'LIMIT') {
      setPrice(realPrice.toFixed(2));
    }
  }, [realPrice, orderType]);

  // 수량 계산 관련
  const calculateMaxQuantity = useCallback(() => {
    if (!account?.available_balance || realPrice <= 0) return 0;
    
    const availableBalance = parseFloat(account.available_balance);
    const orderPrice = orderType === 'MARKET' ? realPrice : (parseFloat(price) || realPrice);
    
    if (orderPrice <= 0) return 0;
    
    const feeMultiplier = 1 + (leverage * FEE_RATE);
    const maxQuantity = availableBalance / (orderPrice * feeMultiplier);
    
    return maxQuantity;
  }, [account, realPrice, orderType, price, leverage]);

  const calculateMaxAmount = useCallback(() => {
    if (!account?.available_balance) return 0;
    return parseFloat(account.available_balance);
  }, [account]);

  // 수량 모드에 따른 값 업데이트
  const updateQuantityByMode = useCallback((mode, value) => {
    const orderPrice = orderType === 'MARKET' ? realPrice : (parseFloat(price) || realPrice);
    if (orderPrice <= 0) return;

    switch(mode) {
      case 'quantity':
        setQuantity(value);
        setAmount((parseFloat(value) * orderPrice).toFixed(2));
        setPercentage(100);
        break;
      case 'amount':
        setAmount(value);
        const qtyFromAmount = parseFloat(value) / orderPrice;
        setQuantity(qtyFromAmount.toFixed(6));
        setPercentage(100);
        break;
      case 'percentage':
        setPercentage(parseFloat(value));
        const maxQty = calculateMaxQuantity();
        const qtyFromPercent = (maxQty * parseFloat(value)) / 100;
        setQuantity(qtyFromPercent.toFixed(6));
        setAmount((qtyFromPercent * orderPrice).toFixed(2));
        break;
    }
  }, [orderType, realPrice, price, calculateMaxQuantity]);

  // 퍼센트 버튼 클릭
  const handlePercentageClick = (percent) => {
    setPercentage(percent);
    updateQuantityByMode('percentage', percent);
  };

  // 주문 계산
  const calculateOrder = useCallback(() => {
    const qty = parseFloat(quantity) || 0;
    const orderPrice = orderType === 'MARKET' ? realPrice : (parseFloat(price) || realPrice);
    
    if (qty <= 0 || orderPrice <= 0) {
      setCalculations({
        positionValue: 0,
        requiredMargin: 0,
        estimatedFee: 0,
        liquidationPrice: 0,
        totalCost: 0,
        actualQuantity: 0,
      });
      return;
    }

    const positionValue = qty * orderPrice * leverage;
    const requiredMargin = qty * orderPrice;
    const estimatedFee = positionValue * FEE_RATE;
    const totalCost = requiredMargin + estimatedFee;

    // 청산가 계산
    const maintenanceMarginRate = 0.004;
    let liquidationPrice;
    
    if (side === 'LONG') {
      liquidationPrice = orderPrice * (1 - (1 / leverage) + maintenanceMarginRate);
    } else {
      liquidationPrice = orderPrice * (1 + (1 / leverage) - maintenanceMarginRate);
    }

    setCalculations({
      positionValue,
      requiredMargin,
      estimatedFee,
      liquidationPrice,
      totalCost,
      actualQuantity: qty,
    });
  }, [quantity, orderType, price, realPrice, leverage, side]);

  useEffect(() => {
    calculateOrder();
  }, [calculateOrder]);

  // 주문 제출
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!account) {
      toast.error('계정 정보를 불러오는 중입니다');
      return;
    }

    const qty = parseFloat(quantity);
    if (!qty || qty <= 0) {
      toast.error('수량을 입력하세요');
      return;
    }

    if (orderType === 'LIMIT') {
      const limitPrice = parseFloat(price);
      if (!limitPrice || limitPrice <= 0) {
        toast.error('지정가를 입력하세요');
        return;
      }
    }

    if (calculations.totalCost > parseFloat(account.available_balance)) {
      toast.error('잔액이 부족합니다');
      return;
    }

    setLoading(true);

    try {
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
        // 초기화
        setQuantity('');
        setAmount('');
        setPercentage(100);
        setPrice('');
        
        toast.success('주문이 체결되었습니다!', {
          autoClose: 1500,
        });
        
        await fetchAccount();
      }
    } catch (error) {
      console.error('주문 실패:', error);
      toast.error(error.message || '주문에 실패했습니다');
    } finally {
      setLoading(false);
    }
  };

  // 렌더링
  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      {/* 헤더 */}
      <div className="flex items-center justify-between p-4 bg-gray-850">
        <h3 className="text-lg font-bold">주문하기</h3>
        <div className="flex items-center space-x-1 text-sm">
          <span className="text-gray-400">사용가능:</span>
          <span className="text-accent font-bold">
            ${account ? parseFloat(account.available_balance).toFixed(2) : '0.00'}
          </span>
        </div>
      </div>

      {/* 메인 폼 */}
      <div className="p-4">
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 1. 방향 선택 */}
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setSide('LONG')}
              className={`py-3 rounded-lg font-bold transition-colors ${
                side === 'LONG'
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
              }`}
            >
              <div className="text-lg">롱</div>
              <div className="text-xs opacity-80">Buy/Long</div>
            </button>
            <button
              type="button"
              onClick={() => setSide('SHORT')}
              className={`py-3 rounded-lg font-bold transition-colors ${
                side === 'SHORT'
                  ? 'bg-red-600 text-white'
                  : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
              }`}
            >
              <div className="text-lg">숏</div>
              <div className="text-xs opacity-80">Sell/Short</div>
            </button>
          </div>

          {/* 2. 주문 타입 */}
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setOrderType('MARKET')}
              className={`py-2 text-sm rounded transition-colors ${
                orderType === 'MARKET'
                  ? 'bg-blue-600 text-white font-semibold'
                  : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
              }`}
            >
              시장가
            </button>
            <button
              type="button"
              onClick={() => setOrderType('LIMIT')}
              className={`py-2 text-sm rounded transition-colors ${
                orderType === 'LIMIT'
                  ? 'bg-blue-600 text-white font-semibold'
                  : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
              }`}
            >
              지정가
            </button>
          </div>

          {/* 3. 지정가 입력 */}
          {orderType === 'LIMIT' && (
            <div className="bg-gray-750 p-3 rounded-lg">
              <div className="flex justify-between items-center mb-2">
                <label className="text-sm text-gray-400">가격 (USDT)</label>
                <span className="text-xs text-gray-500">
                  현재가: ${formatPrice(realPrice)}
                </span>
              </div>
              <div className="relative">
                <input
                  type="number"
                  step="0.01"
                  value={price}
                  onChange={(e) => {
                    setPrice(e.target.value);
                    updateQuantityByMode(quantityMode, 
                      quantityMode === 'quantity' ? quantity :
                      quantityMode === 'amount' ? amount :
                      percentage.toString()
                    );
                  }}
                  className="w-full px-4 py-2 bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                  placeholder="지정가 입력"
                />
                <div className="absolute right-2 top-1/2 transform -translate-y-1/2">
                  <button
                    type="button"
                    onClick={() => setPrice(realPrice.toFixed(2))}
                    className="text-xs px-2 py-1 bg-gray-600 hover:bg-gray-500 rounded"
                  >
                    현재가
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 4. 레버리지 설정 */}
          <div className="bg-gray-750 p-3 rounded-lg">
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm text-gray-400">레버리지</label>
              <span className="text-xl font-bold text-accent">{leverage}x</span>
            </div>
            <div className="flex flex-wrap gap-2 mb-2">
              {[1, 3, 5, 10, 20, 50].map((lev) => (
                <button
                  key={lev}
                  type="button"
                  onClick={() => setLeverage(lev)}
                  className={`px-3 py-1.5 text-sm rounded transition-colors ${
                    leverage === lev
                      ? 'bg-accent text-dark font-bold'
                      : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                  }`}
                >
                  {lev}x
                </button>
              ))}
            </div>
            <input
              type="range"
              min="1"
              max="125"
              value={leverage}
              onChange={(e) => setLeverage(parseInt(e.target.value))}
              className="w-full"
            />
          </div>

          {/* 5. 수량 설정 */}
          <div className="bg-gray-750 p-3 rounded-lg">
            {/* 수량 모드 탭 */}
            <div className="flex mb-3 border-b border-gray-600">
              {[
                { id: 'quantity', label: '수량' },
                { id: 'amount', label: '금액' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => {
                    setQuantityMode(tab.id);
                    updateQuantityByMode(tab.id, 
                      tab.id === 'quantity' ? quantity :
                      tab.id === 'amount' ? amount :
                      percentage.toString()
                    );
                  }}
                  className={`flex-1 py-2 text-sm border-b-2 transition-colors ${
                    quantityMode === tab.id
                      ? 'border-accent text-accent font-semibold'
                      : 'border-transparent text-gray-400 hover:text-gray-300'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* 수량 입력 필드 */}
            <div className="mb-3">
              {quantityMode === 'quantity' && (
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs text-gray-400">수량 (BTC)</span>
                    <span className="text-xs text-gray-500">
                      최대: {calculateMaxQuantity().toFixed(6)}
                    </span>
                  </div>
                  <input
                    type="number"
                    step="0.000001"
                    value={quantity}
                    onChange={(e) => updateQuantityByMode('quantity', e.target.value)}
                    className="w-full px-4 py-2 bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-accent font-mono text-right"
                    placeholder="0.000000"
                  />
                </div>
              )}
              
              {quantityMode === 'amount' && (
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs text-gray-400">금액 (USDT)</span>
                    <span className="text-xs text-gray-500">
                      최대: ${calculateMaxAmount().toFixed(2)}
                    </span>
                  </div>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">$</span>
                    <input
                      type="number"
                      step="0.01"
                      value={amount}
                      onChange={(e) => updateQuantityByMode('amount', e.target.value)}
                      className="w-full pl-8 pr-4 py-2 bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-accent font-mono text-right"
                      placeholder="0.00"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* 퍼센트 버튼들 */}
            <div className="grid grid-cols-4 gap-2">
              {[25, 50, 75, 100].map((percent) => (
                <button
                  key={percent}
                  type="button"
                  onClick={() => handlePercentageClick(percent)}
                  className={`py-2 text-sm rounded transition-colors ${
                    percentage === percent
                      ? 'bg-accent/20 text-accent font-bold border border-accent/50'
                      : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                  }`}
                >
                  {percent}%
                </button>
              ))}
            </div>
          </div>

          {/* 6. 주문 정보 요약 */}
          <div className="bg-gray-750 p-4 rounded-lg space-y-3">
            <div className="flex justify-between items-center pb-2 border-b border-gray-600">
              <span className="text-gray-400">주문 요약</span>
              <span className={`text-sm font-semibold ${side === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>
                {side === 'LONG' ? '롱' : '숏'} • {leverage}x
              </span>
            </div>
            
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-gray-400 text-xs mb-1">포지션 가치</div>
                <div className="font-semibold">${formatPrice(calculations.positionValue)}</div>
              </div>
              <div>
                <div className="text-gray-400 text-xs mb-1">필요 증거금</div>
                <div className="font-semibold">${formatPrice(calculations.requiredMargin)}</div>
              </div>
              <div>
                <div className="text-gray-400 text-xs mb-1">예상 수수료</div>
                <div className="font-semibold text-yellow-400">${calculations.estimatedFee.toFixed(2)}</div>
              </div>
              <div>
                <div className="text-gray-400 text-xs mb-1">실제 수량</div>
                <div className="font-semibold">{calculations.actualQuantity.toFixed(6)} BTC</div>
              </div>
            </div>
            
            <div className="pt-2 border-t border-gray-600">
              <div className="flex justify-between">
                <div>
                  <div className="text-gray-400 text-xs mb-1">청산가</div>
                  <div className="text-orange-400 font-semibold">
                    ${formatPrice(calculations.liquidationPrice)}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-gray-400 text-xs mb-1">총 비용</div>
                  <div className="font-bold">${calculations.totalCost.toFixed(2)}</div>
                </div>
              </div>
            </div>
          </div>

          {/* 7. 주문 버튼 */}
          <button
            type="submit"
            disabled={loading || !quantity || parseFloat(quantity) <= 0}
            className={`w-full py-3 rounded-lg font-bold text-lg transition-colors ${
              side === 'LONG'
                ? 'bg-green-600 hover:bg-green-700'
                : 'bg-red-600 hover:bg-red-700'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {loading ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                처리 중...
              </div>
            ) : (
              `${side === 'LONG' ? '롱' : '숏'} 주문 (${leverage}x)`
            )}
          </button>

          {/* 8. 안내 메시지 */}
          <div className="text-center text-xs text-gray-500">
            주문 전 설정을 다시 확인해주세요.
          </div>
        </form>
      </div>
    </div>
  );
};

export default FuturesOrderForm;