// client/src/components/trading/OrderForm.js
import React, { useState, useEffect } from 'react';
import axios from '../../api/axios';
import { toast } from 'react-toastify';

const OrderForm = ({ symbol, currentPrice, onOrderTypeChange, orderType = 'MARKET' }) => {
  const [side, setSide] = useState('BUY');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [balance, setBalance] = useState(0);
  const [position, setPosition] = useState(null); // 보유 포지션 정보
  const [percentage, setPercentage] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchBalance();
    if (symbol) {
      fetchPosition();
    }
  }, [symbol]);

  const fetchBalance = async () => {
    try {
      const response = await axios.get('/api/v1/account/');
      setBalance(response.data.balance);
    } catch (error) {
      console.error('잔액 조회 실패:', error);
    }
  };

  const fetchPosition = async () => {
    try {
      const response = await axios.get(`/api/v1/account/positions/${symbol}`);
      setPosition(response.data);
    } catch (error) {
      console.error('포지션 조회 실패:', error);
      setPosition(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!quantity || parseFloat(quantity) <= 0) {
      toast.error('수량을 입력하세요');
      return;
    }

    if (orderType === 'LIMIT' && (!price || parseFloat(price) <= 0)) {
      toast.error('가격을 입력하세요');
      return;
    }

    setLoading(true);

    try {
      const orderData = {
        symbol: symbol,
        side: side,
        order_type: orderType,
        quantity: parseFloat(quantity),
        price: orderType === 'LIMIT' ? parseFloat(price) : undefined
      };

      const response = await axios.post('/api/v1/orders/', orderData);
      
      const order = response.data;
      const qty = parseFloat(order.quantity);
      const fillPrice = orderType === 'MARKET' ? currentPrice : parseFloat(price);
      const total = qty * fillPrice;
      
      if (order.status === 'FILLED') {
        toast.success(
          `✅ ${side === 'BUY' ? '매수' : '매도'} 체결 완료!\n` +
          `코인: ${symbol.replace('USDT', '')}\n` +
          `수량: ${qty.toFixed(8)}\n` +
          `가격: $${fillPrice.toFixed(2)}\n` +
          `총액: $${total.toFixed(2)}`,
          { 
            autoClose: 5000,
            position: 'top-center'
          }
        );
      } else {
        toast.success(
          `📝 지정가 주문 등록!\n` +
          `${side === 'BUY' ? '매수' : '매도'} ${qty.toFixed(8)} ${symbol.replace('USDT', '')}\n` +
          `목표가: $${parseFloat(price).toFixed(2)}\n` +
          `현재가가 목표가에 도달하면 자동으로 체결됩니다`,
          { 
            autoClose: 7000,
            position: 'top-center'
          }
        );
      }
      
      setQuantity('');
      setPrice('');
      setPercentage(0);
      
      // 잔액 및 포지션 새로고침
      await fetchBalance();
      await fetchPosition();
      
    } catch (error) {
      console.error('❌ Order error:', error);
      
      let errorMsg = '주문 실패';
      
      if (error.response?.data?.detail) {
        errorMsg = error.response.data.detail;
      } else if (error.response?.status === 500) {
        errorMsg = '서버 오류가 발생했습니다';
      } else if (error.response?.status === 400) {
        errorMsg = '잘못된 주문입니다';
      } else if (!error.response) {
        errorMsg = '서버 연결 실패';
      }
      
      toast.error(`❌ ${errorMsg}`, { autoClose: 5000 });
      
    } finally {
      setLoading(false);
    }
  };

  const calculateTotal = () => {
    const qty = parseFloat(quantity) || 0;
    const prc = orderType === 'MARKET' ? currentPrice : parseFloat(price) || 0;
    return (qty * prc).toFixed(2);
  };

  // 퍼센트 계산 (수수료 제거됨)
  const handlePercentageClick = (percent) => {
    setPercentage(percent);
    
    if (side === 'BUY') {
      // 매수: 사용 가능한 잔액의 퍼센트만큼 계산
      const usableBalance = balance * (percent / 100);
      const calculatedPrice = orderType === 'MARKET' ? currentPrice : parseFloat(price) || currentPrice;
      
      if (calculatedPrice > 0) {
        const calculatedQty = usableBalance / calculatedPrice;
        setQuantity(calculatedQty > 0 ? calculatedQty.toFixed(8) : '0');
      }
    } else {
      // 매도: 주문 가능 수량의 퍼센트만큼 계산
      if (position && position.available_quantity > 0) {
        const calculatedQty = position.available_quantity * (percent / 100);
        setQuantity(calculatedQty > 0 ? calculatedQty.toFixed(8) : '0');
      } else {
        toast.warning('매도 가능한 수량이 없습니다');
        setQuantity('0');
      }
    }
  };

  const adjustQuantity = (delta) => {
    const currentQty = parseFloat(quantity) || 0;
    const newQty = Math.max(0, currentQty + delta);
    setQuantity(newQty > 0 ? newQty.toFixed(8) : '');
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h2 className="text-xl font-bold mb-6">주문하기</h2>

      {/* 주문 타입 선택 */}
      <div className="flex space-x-2 mb-6">
        <button
          onClick={() => onOrderTypeChange('MARKET')}
          className={`flex-1 py-2 rounded-lg transition-colors ${
            orderType === 'MARKET' 
              ? 'bg-accent text-dark font-semibold' 
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          시장가
        </button>
        <button
          onClick={() => onOrderTypeChange('LIMIT')}
          className={`flex-1 py-2 rounded-lg transition-colors ${
            orderType === 'LIMIT' 
              ? 'bg-accent text-dark font-semibold' 
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          지정가
        </button>
      </div>

      {/* 매수/매도 선택 */}
      <div className="flex space-x-2 mb-6">
        <button
          onClick={() => setSide('BUY')}
          className={`flex-1 py-3 rounded-lg font-semibold transition-colors ${
            side === 'BUY' 
              ? 'bg-green-600 text-white' 
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          매수
        </button>
        <button
          onClick={() => setSide('SELL')}
          className={`flex-1 py-3 rounded-lg font-semibold transition-colors ${
            side === 'SELL' 
              ? 'bg-red-600 text-white' 
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          매도
        </button>
      </div>

      {/* 포지션 정보 (매도 시에만 표시) */}
      {side === 'SELL' && position && position.quantity > 0 && (
        <div className="bg-gray-700 rounded-lg p-4 mb-4 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">보유 수량:</span>
            <span className="text-white font-semibold">{position.quantity.toFixed(8)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">미체결 주문:</span>
            <span className="text-yellow-400">{position.locked_quantity.toFixed(8)}</span>
          </div>
          <div className="flex justify-between text-sm border-t border-gray-600 pt-2">
            <span className="text-gray-400">주문 가능:</span>
            <span className="text-green-400 font-bold">{position.available_quantity.toFixed(8)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">평균 매수가:</span>
            <span className="text-white">${position.average_price.toFixed(2)}</span>
          </div>
        </div>
      )}

      {/* 가격 입력 (지정가만) */}
      {orderType === 'LIMIT' && (
        <div className="mb-4">
          <label className="block text-sm text-gray-400 mb-2">
            주문 가격 (USDT)
          </label>
          <input
            type="number"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="가격 입력"
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-accent"
            step="0.01"
          />
        </div>
      )}

      {/* 수량 입력 */}
      <div className="mb-4">
        <label className="block text-sm text-gray-400 mb-2">
          주문 수량
        </label>
        <div className="flex space-x-2">
          <input
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="수량 입력"
            className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-accent"
            step="0.00000001"
          />
          <button
            onClick={() => adjustQuantity(0.01)}
            className="bg-gray-700 hover:bg-gray-600 px-4 rounded-lg"
          >
            +
          </button>
          <button
            onClick={() => adjustQuantity(-0.01)}
            className="bg-gray-700 hover:bg-gray-600 px-4 rounded-lg"
          >
            -
          </button>
        </div>
      </div>

      {/* 퍼센트 버튼 */}
      <div className="grid grid-cols-4 gap-2 mb-6">
        {[25, 50, 75, 100].map((pct) => (
          <button
            key={pct}
            onClick={() => handlePercentageClick(pct)}
            className={`py-2 rounded-lg transition-colors ${
              percentage === pct
                ? 'bg-accent text-dark font-semibold'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {pct}%
          </button>
        ))}
      </div>

      {/* 주문 정보 요약 */}
      <div className="bg-gray-700 rounded-lg p-4 mb-6 space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">
            {side === 'BUY' ? '사용 가능 잔액:' : '주문 가능 수량:'}
          </span>
          <span className="text-white font-semibold">
            {side === 'BUY' 
              ? `$${balance.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}`
              : position 
                ? `${position.available_quantity.toFixed(8)} ${symbol.replace('USDT', '')}`
                : '0.00000000'
            }
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">주문 금액:</span>
          <span className="text-accent font-semibold">${calculateTotal()}</span>
        </div>
      </div>

      {/* 주문 버튼 */}
      <button
        onClick={handleSubmit}
        disabled={loading}
        className={`w-full py-4 rounded-lg font-bold text-lg transition-colors ${
          side === 'BUY'
            ? 'bg-green-600 hover:bg-green-700 text-white'
            : 'bg-red-600 hover:bg-red-700 text-white'
        } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        {loading ? '처리 중...' : `${side === 'BUY' ? '매수' : '매도'} 주문`}
      </button>

      {/* 안내 메시지 */}
      {orderType === 'MARKET' && (
        <p className="text-xs text-gray-500 mt-4 text-center">
          시장가 주문은 즉시 체결됩니다
        </p>
      )}
      {orderType === 'LIMIT' && (
        <p className="text-xs text-gray-500 mt-4 text-center">
          지정가 주문은 목표가 도달 시 자동 체결됩니다
        </p>
      )}
    </div>
  );
};

export default OrderForm;