// client/src/components/trading/OrderForm.js
import React, { useState, useEffect } from 'react';
import axios from '../../api/axios';
import { toast } from 'react-toastify';

const OrderForm = ({ symbol, currentPrice, orderType, onOrderTypeChange }) => {
  const [side, setSide] = useState('BUY');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [balance, setBalance] = useState(0);
  const [loading, setLoading] = useState(false);
  const [percentage, setPercentage] = useState(0);

  useEffect(() => {
    fetchBalance();
  }, []);

  useEffect(() => {
    if (orderType === 'MARKET') {
      setPrice(currentPrice.toString());
    }
  }, [orderType, currentPrice]);

  const fetchBalance = async () => {
    try {
      const response = await axios.get('/api/v1/account/');
      setBalance(parseFloat(response.data.balance));
    } catch (error) {
      console.error('Failed to fetch balance:', error);
    }
  };

const handleSubmit = async (e) => {
  e.preventDefault();
  
  const qty = parseFloat(quantity);
  if (!qty || qty <= 0) {
    toast.error('수량을 입력해주세요');
    return;
  }

  if (orderType === 'LIMIT' && (!price || parseFloat(price) <= 0)) {
    toast.error('가격을 입력해주세요');
    return;
  }

  // 잔액 검증
  if (side === 'BUY') {
    const orderPrice = orderType === 'MARKET' ? currentPrice : parseFloat(price);
    const total = qty * orderPrice;
    const fee = total * 0.001;
    const required = total + fee;
    
    if (balance < required) {
      toast.error(
        `💰 잔액 부족\n보유: $${balance.toFixed(2)}\n필요: $${required.toFixed(2)}`,
        { autoClose: 5000 }
      );
      return;
    }
  }

  setLoading(true);

  try {
    const orderData = {
      symbol,
      side,
      order_type: orderType,
      quantity: qty,
    };

    if (orderType === 'LIMIT') {
      orderData.price = parseFloat(price);
    }

    console.log('📤 Sending order:', orderData);
    
    const response = await axios.post('/api/v1/orders/', orderData);
    
    console.log('✅ Order response:', response.data);
    
    // ✅ 주문 완료 알림
    if (orderType === 'MARKET') {
      const fillPrice = response.data.average_price || currentPrice;
      const total = qty * fillPrice;
      
      toast.success(
        `🎉 ${side === 'BUY' ? '매수' : '매도'} 체결 완료!\n` +
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
    
    // 잔액 새로고침
    await fetchBalance();
    
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

  // ✅ 수정: 퍼센트 계산 로직 (수수료 포함)
  const handlePercentageClick = (percent) => {
    setPercentage(percent);
    
    if (side === 'BUY') {
      const usableBalance = balance * (percent / 100);
      const calculatedPrice = orderType === 'MARKET' ? currentPrice : parseFloat(price) || currentPrice;
      
      if (calculatedPrice > 0) {
        // ✅ 수수료 0.1%를 고려한 계산
        // usableBalance = (price * qty) + (price * qty * 0.001)
        // usableBalance = price * qty * 1.001
        // qty = usableBalance / (price * 1.001)
        const calculatedQty = usableBalance / (calculatedPrice * 1.001);
        setQuantity(calculatedQty > 0 ? calculatedQty.toFixed(8) : '0');
      }
    } else {
      toast.info('매도 퍼센트 기능은 포트폴리오 정보 연동 후 사용 가능합니다');
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

      <div className="flex space-x-2 mb-6">
        <button
          onClick={() => onOrderTypeChange('MARKET')}
          className={`flex-1 py-2 rounded-lg transition-colors ${
            orderType === 'MARKET' 
              ? 'bg-accent text-white' 
              : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
          }`}
        >
          시장가
        </button>
        <button
          onClick={() => onOrderTypeChange('LIMIT')}
          className={`flex-1 py-2 rounded-lg transition-colors ${
            orderType === 'LIMIT' 
              ? 'bg-accent text-white' 
              : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
          }`}
        >
          지정가
        </button>
      </div>

      <div className="flex space-x-2 mb-6">
        <button
          onClick={() => setSide('BUY')}
          className={`flex-1 py-2 rounded-lg transition-colors ${
            side === 'BUY' 
              ? 'bg-green-600 text-white' 
              : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
          }`}
        >
          매수
        </button>
        <button
          onClick={() => setSide('SELL')}
          className={`flex-1 py-2 rounded-lg transition-colors ${
            side === 'SELL' 
              ? 'bg-red-600 text-white' 
              : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
          }`}
        >
          매도
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {orderType === 'LIMIT' && (
          <div>
            <label className="block text-sm text-gray-400 mb-2">가격 (USDT)</label>
            <input
              type="number"
              step="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              className="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent"
              placeholder="주문 가격"
              required
            />
          </div>
        )}

        <div>
          <label className="block text-sm text-gray-400 mb-2">수량</label>
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={() => adjustQuantity(-0.001)}
              className="px-4 py-3 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors font-bold"
            >
              −
            </button>
            <input
              type="number"
              step="0.00000001"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="flex-1 p-3 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent text-center"
              placeholder="주문 수량"
              required
            />
            <button
              type="button"
              onClick={() => adjustQuantity(0.001)}
              className="px-4 py-3 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors font-bold"
            >
              +
            </button>
          </div>
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-2">
            {side === 'BUY' ? '잔액 비율' : '보유량 비율'}
          </label>
          <div className="grid grid-cols-4 gap-2">
            {[25, 50, 75, 100].map((percent) => (
              <button
                key={percent}
                type="button"
                onClick={() => handlePercentageClick(percent)}
                className={`py-2 rounded-lg transition-colors font-semibold ${
                  percentage === percent
                    ? 'bg-accent text-white'
                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                }`}
              >
                {percent}%
              </button>
            ))}
          </div>
        </div>

        <div className="bg-gray-700 rounded-lg p-4 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">보유 현금</span>
            <span className="font-semibold">${balance.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">주문 총액</span>
            <span className="font-semibold">${calculateTotal()}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">예상 수수료 (0.1%)</span>
            <span className="font-semibold text-yellow-400">
              ${(parseFloat(calculateTotal()) * 0.001).toFixed(2)}
            </span>
          </div>
          {orderType === 'MARKET' && (
            <div className="text-xs text-gray-500 mt-2">
              * 시장가 주문은 즉시 현재가로 체결됩니다
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className={`w-full py-3 rounded-lg font-semibold transition-colors ${
            side === 'BUY'
              ? 'bg-green-600 hover:bg-green-700'
              : 'bg-red-600 hover:bg-red-700'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {loading ? '처리 중...' : side === 'BUY' ? '매수하기' : '매도하기'}
        </button>
      </form>
    </div>
  );
};

export default OrderForm;