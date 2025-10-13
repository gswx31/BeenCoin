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
    setLoading(true);

    try {
      const orderData = {
        symbol,
        side,
        order_type: orderType,
        quantity: parseFloat(quantity),
      };

      if (orderType === 'LIMIT') {
        orderData.price = parseFloat(price);
      }

      await axios.post('/api/v1/orders/', orderData);
      toast.success(`${side === 'BUY' ? '매수' : '매도'} 주문이 체결되었습니다!`);
      
      setQuantity('');
      setPrice('');
      fetchBalance();
    } catch (error) {
      toast.error(error.response?.data?.detail || '주문 실패');
    } finally {
      setLoading(false);
    }
  };

  const calculateTotal = () => {
    const qty = parseFloat(quantity) || 0;
    const prc = orderType === 'MARKET' ? currentPrice : parseFloat(price) || 0;
    return (qty * prc).toFixed(2);
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h2 className="text-xl font-bold mb-6">주문하기</h2>

      <div className="flex space-x-2 mb-6">
        <button
          onClick={() => onOrderTypeChange('MARKET')}
          className={`flex-1 py-2 rounded-lg ${orderType === 'MARKET' ? 'bg-accent text-white' : 'bg-gray-700 text-gray-400'}`}
        >
          시장가
        </button>
        <button
          onClick={() => onOrderTypeChange('LIMIT')}
          className={`flex-1 py-2 rounded-lg ${orderType === 'LIMIT' ? 'bg-accent text-white' : 'bg-gray-700 text-gray-400'}`}
        >
          지정가
        </button>
      </div>

      <div className="flex space-x-2 mb-6">
        <button
          onClick={() => setSide('BUY')}
          className={`flex-1 py-2 rounded-lg ${side === 'BUY' ? 'bg-green-600 text-white' : 'bg-gray-700 text-gray-400'}`}
        >
          매수
        </button>
        <button
          onClick={() => setSide('SELL')}
          className={`flex-1 py-2 rounded-lg ${side === 'SELL' ? 'bg-red-600 text-white' : 'bg-gray-700 text-gray-400'}`}
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
          <input
            type="number"
            step="0.00000001"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent"
            placeholder="주문 수량"
            required
          />
        </div>

        <div className="bg-gray-700 rounded-lg p-4 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">보유 현금</span>
            <span className="font-semibold">${balance.toLocaleString('ko-KR')}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">주문 총액</span>
            <span className="font-semibold">${calculateTotal()}</span>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className={`w-full py-3 rounded-lg font-semibold ${
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