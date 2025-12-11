// client/src/components/trading/FuturesOrderForm.js
// =============================================================================
// 선물 주문 폼 - 단타 설정 저장 + 손절/익절 직접 입력
// =============================================================================
import React, { useState, useEffect, useCallback } from 'react';
import { useFutures } from '../../contexts/FuturesContext';
import { useMarket } from '../../contexts/MarketContext';
import { formatPrice } from '../../utils/formatPrice';
import { toast } from 'react-toastify';
import { 
  loadScalperSettings, 
  saveScalperSettings,
  defaultScalperSettings 
} from '../../utils/scalperSettings';

const FEE_RATE = 0.0004; // 0.04%

const FuturesOrderForm = ({ symbol, currentPrice }) => {
  const { account, openPosition, fetchAccount } = useFutures();
  const { realtimePrices } = useMarket();

  const [side, setSide] = useState('LONG');
  const [orderType, setOrderType] = useState('MARKET');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [leverage, setLeverage] = useState(10);
  
  // 🆕 손절/익절 설정
  const [stopLossEnabled, setStopLossEnabled] = useState(false);
  const [takeProfitEnabled, setTakeProfitEnabled] = useState(false);
  const [stopLossPrice, setStopLossPrice] = useState('');
  const [takeProfitPrice, setTakeProfitPrice] = useState('');
  
  // 🆕 단타 모드 - 저장된 설정 불러오기
  const [scalperSettings, setScalperSettings] = useState(() => loadScalperSettings());
  const [showSettings, setShowSettings] = useState(false);
  
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
  // 🆕 컴포넌트 마운트 시 저장된 단타 설정 적용
  // ===========================================
  useEffect(() => {
    const saved = loadScalperSettings();
    setScalperSettings(saved);
  }, []);

  // ===========================================
  // 최대 주문 가능 수량 계산
  // ===========================================
  const calculateMaxQuantity = useCallback(() => {
    if (!account?.available_balance || realPrice <= 0) return 0;
    
    const availableBalance = parseFloat(account.available_balance);
    const orderPrice = orderType === 'MARKET' ? realPrice : (parseFloat(price) || realPrice);
    
    if (orderPrice <= 0) return 0;
    
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
    });
  }, [quantity, orderType, price, realPrice, leverage, side]);

  useEffect(() => {
    calculateOrder();
  }, [calculateOrder]);

  // ===========================================
  // 🆕 단타 모드 활성화 시 자동 계산
  // ===========================================
  useEffect(() => {
    if (scalperSettings.enabled && realPrice > 0) {
      const orderPrice = orderType === 'MARKET' ? realPrice : (parseFloat(price) || realPrice);
      
      if (orderPrice <= 0) return;
      
      const slPercent = scalperSettings.stopLossPercent;
      const tpPercent = scalperSettings.takeProfitPercent;
      
      if (side === 'LONG') {
        setStopLossPrice((orderPrice * (1 - slPercent / 100)).toFixed(2));
        setTakeProfitPrice((orderPrice * (1 + tpPercent / 100)).toFixed(2));
      } else {
        setStopLossPrice((orderPrice * (1 + slPercent / 100)).toFixed(2));
        setTakeProfitPrice((orderPrice * (1 - tpPercent / 100)).toFixed(2));
      }
      
      setStopLossEnabled(true);
      setTakeProfitEnabled(true);
    }
  }, [scalperSettings.enabled, scalperSettings.stopLossPercent, scalperSettings.takeProfitPercent, realPrice, orderType, price, side]);

  // ===========================================
  // 🆕 단타 모드 토글 및 저장
  // ===========================================
  const toggleScalperMode = () => {
    const newSettings = {
      ...scalperSettings,
      enabled: !scalperSettings.enabled,
    };
    setScalperSettings(newSettings);
    saveScalperSettings(newSettings);
    
    if (!newSettings.enabled) {
      // 단타 모드 끄면 손절/익절 초기화
      setStopLossEnabled(false);
      setTakeProfitEnabled(false);
      setStopLossPrice('');
      setTakeProfitPrice('');
    }
  };

  // ===========================================
  // 🆕 단타 설정 변경 및 저장
  // ===========================================
  const updateScalperSettings = (field, value) => {
    const newSettings = {
      ...scalperSettings,
      [field]: parseFloat(value) || 0,
    };
    setScalperSettings(newSettings);
    saveScalperSettings(newSettings);
  };

  // ===========================================
  // 100% 주문
  // ===========================================
  const handleMaxOrder = () => {
    const maxQty = calculateMaxQuantity();
    if (maxQty > 0) {
      setQuantity(maxQty.toFixed(6));
    }
  };

  // ===========================================
  // 주문 제출
  // ===========================================
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
        stopLossPrice: stopLossEnabled ? parseFloat(stopLossPrice) : undefined,
        takeProfitPrice: takeProfitEnabled ? parseFloat(takeProfitPrice) : undefined,
      };

      const result = await openPosition(orderData);

      if (result.success) {
        setQuantity('');
        setPrice('');
        // 단타 모드가 아니면 손절/익절도 초기화
        if (!scalperSettings.enabled) {
          setStopLossPrice('');
          setTakeProfitPrice('');
          setStopLossEnabled(false);
          setTakeProfitEnabled(false);
        }
        await fetchAccount();
      }
    } catch (error) {
      console.error('주문 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  // ===========================================
  // 렌더링
  // ===========================================
  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-bold">주문</h3>
        <button
          type="button"
          onClick={() => setShowSettings(!showSettings)}
          className="text-gray-400 hover:text-accent"
          title="단타 설정"
        >
          ⚙️
        </button>
      </div>

      {/* 🆕 단타 설정 패널 */}
      {showSettings && (
        <div className="mb-4 p-4 bg-gray-700 rounded">
          <h4 className="text-sm font-semibold mb-3">단타 모드 기본 설정</h4>
          
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm text-gray-400">기본 활성화</label>
              <button
                type="button"
                onClick={toggleScalperMode}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  scalperSettings.enabled ? 'bg-accent' : 'bg-gray-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    scalperSettings.enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className="flex items-center space-x-2">
              <label className="text-xs text-gray-400 w-20">손절:</label>
              <input
                type="number"
                step="0.1"
                value={scalperSettings.stopLossPercent}
                onChange={(e) => updateScalperSettings('stopLossPercent', e.target.value)}
                className="flex-1 px-2 py-1 bg-gray-600 rounded text-sm"
              />
              <span className="text-xs text-gray-400">%</span>
            </div>

            <div className="flex items-center space-x-2">
              <label className="text-xs text-gray-400 w-20">익절:</label>
              <input
                type="number"
                step="0.1"
                value={scalperSettings.takeProfitPercent}
                onChange={(e) => updateScalperSettings('takeProfitPercent', e.target.value)}
                className="flex-1 px-2 py-1 bg-gray-600 rounded text-sm"
              />
              <span className="text-xs text-gray-400">%</span>
            </div>
          </div>

          <p className="text-xs text-gray-500 mt-3">
            💡 이 설정은 저장되어 다음 주문에도 자동으로 적용됩니다
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* 방향 선택 */}
        <div className="flex space-x-2">
          <button
            type="button"
            onClick={() => setSide('LONG')}
            className={`flex-1 py-2 rounded font-semibold transition-colors ${
              side === 'LONG'
                ? 'bg-green-600 text-white'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
          >
            롱 (매수)
          </button>
          <button
            type="button"
            onClick={() => setSide('SHORT')}
            className={`flex-1 py-2 rounded font-semibold transition-colors ${
              side === 'SHORT'
                ? 'bg-red-600 text-white'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
          >
            숏 (매도)
          </button>
        </div>

        {/* 주문 타입 */}
        <div className="flex space-x-2">
          <button
            type="button"
            onClick={() => setOrderType('MARKET')}
            className={`flex-1 py-2 rounded transition-colors ${
              orderType === 'MARKET'
                ? 'bg-accent text-dark font-semibold'
                : 'bg-gray-700 text-gray-400'
            }`}
          >
            시장가
          </button>
          <button
            type="button"
            onClick={() => setOrderType('LIMIT')}
            className={`flex-1 py-2 rounded transition-colors ${
              orderType === 'LIMIT'
                ? 'bg-accent text-dark font-semibold'
                : 'bg-gray-700 text-gray-400'
            }`}
          >
            지정가
          </button>
        </div>

        {/* 레버리지 */}
        <div>
          <label className="block text-sm text-gray-400 mb-2">
            레버리지: {leverage}x
          </label>
          <input
            type="range"
            min="1"
            max="125"
            value={leverage}
            onChange={(e) => setLeverage(parseInt(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>1x</span>
            <span>25x</span>
            <span>50x</span>
            <span>125x</span>
          </div>
        </div>

        {/* 지정가 (LIMIT 주문 시) */}
        {orderType === 'LIMIT' && (
          <div>
            <label className="block text-sm text-gray-400 mb-2">지정가 (USDT)</label>
            <input
              type="number"
              step="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder={`현재가: ${formatPrice(realPrice)}`}
              className="w-full px-4 py-2 bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-accent"
            />
            <p className="text-xs text-gray-500 mt-1">
              💡 현재가보다 낮은 가격 = 조건부 매수 대기
            </p>
          </div>
        )}

        {/* 수량 */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm text-gray-400">수량</label>
            <button
              type="button"
              onClick={handleMaxOrder}
              className="text-xs text-accent hover:underline"
            >
              최대
            </button>
          </div>
          <input
            type="number"
            step="0.000001"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="0.000000"
            className="w-full px-4 py-2 bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-accent"
            required
          />
        </div>

        {/* 🆕 단타 모드 상태 표시 */}
        {scalperSettings.enabled && (
          <div className="bg-accent/20 border border-accent/50 rounded p-3">
            <div className="flex items-center space-x-2 mb-1">
              <span className="text-accent font-semibold text-sm">⚡ 단타 모드 활성</span>
            </div>
            <p className="text-xs text-gray-400">
              손절 {scalperSettings.stopLossPercent}% / 익절 {scalperSettings.takeProfitPercent}% 자동 설정됨
            </p>
          </div>
        )}

        {/* 🆕 수동 손절/익절 (단타 모드가 아닐 때만) */}
        {!scalperSettings.enabled && (
          <div className="border-t border-gray-700 pt-4 space-y-3">
            {/* 손절 */}
            <div>
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

            {/* 익절 */}
            <div>
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
          </div>
        )}

        {/* 주문 요약 */}
        <div className="bg-gray-700/50 p-4 rounded space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">포지션 가치:</span>
            <span className="font-semibold">${formatPrice(calculations.positionValue)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">필요 증거금:</span>
            <span>${formatPrice(calculations.requiredMargin)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">예상 수수료:</span>
            <span className="text-red-400">${calculations.estimatedFee.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">청산가:</span>
            <span className="text-orange-400">${formatPrice(calculations.liquidationPrice)}</span>
          </div>
          {stopLossEnabled && stopLossPrice && (
            <div className="flex justify-between">
              <span className="text-gray-400">손절가:</span>
              <span className="text-red-400">${parseFloat(stopLossPrice).toFixed(2)}</span>
            </div>
          )}
          {takeProfitEnabled && takeProfitPrice && (
            <div className="flex justify-between">
              <span className="text-gray-400">익절가:</span>
              <span className="text-green-400">${parseFloat(takeProfitPrice).toFixed(2)}</span>
            </div>
          )}
          <div className="flex justify-between pt-2 border-t border-gray-600">
            <span className="text-gray-400 font-semibold">총 비용:</span>
            <span className="font-bold">${calculations.totalCost.toFixed(2)}</span>
          </div>
        </div>

        {/* 주문 버튼 */}
        <button
          type="submit"
          disabled={loading || !quantity}
          className={`w-full py-3 rounded-lg font-bold transition-colors ${
            side === 'LONG'
              ? 'bg-green-600 hover:bg-green-700'
              : 'bg-red-600 hover:bg-red-700'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {loading ? '처리 중...' : `${side === 'LONG' ? '롱' : '숏'} 진입 (${leverage}x)`}
        </button>

        {/* 잔액 표시 */}
        {account && (
          <div className="text-center text-sm text-gray-400">
            사용 가능: ${parseFloat(account.available_balance).toFixed(2)} USDT
          </div>
        )}
      </form>
    </div>
  );
};

export default FuturesOrderForm;