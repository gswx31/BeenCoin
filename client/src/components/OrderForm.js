import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';

const OrderForm = () => {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [side, setSide] = useState('BUY');
  const [orderType, setOrderType] = useState('MARKET');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const token = localStorage.getItem('token');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/api/v1/orders', {
        symbol,
        side,
        order_type: orderType,
        quantity: parseFloat(quantity),
        price: orderType === 'LIMIT' ? parseFloat(price) : undefined
      }, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success('주문 성공!');
      navigate('/dashboard');
    } catch (error) {
      toast.error('주문 실패: ' + (error.response?.data?.detail || '오류 발생'));
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10 p-6 bg-white rounded-lg shadow-xl">
      <h2 className="text-2xl font-bold mb-4">주문 하기</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <select
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-accent"
        >
          <option>BTCUSDT</option>
          <option>ETHUSDT</option>
          <option>BNBUSDT</option>
        </select>
        <select
          value={side}
          onChange={(e) => setSide(e.target.value)}
          className="w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-accent"
        >
          <option>BUY</option>
          <option>SELL</option>
        </select>
        <select
          value={orderType}
          onChange={(e) => setOrderType(e.target.value)}
          className="w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-accent"
        >
          <option>MARKET</option>
          <option>LIMIT</option>
        </select>
        <input
          type="number"
          placeholder="수량"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          className="w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-accent"
        />
        {orderType === 'LIMIT' && (
          <input
            type="number"
            placeholder="가격"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-accent"
          />
        )}
        <button type="submit" className="w-full p-2 bg-accent text-white rounded hover:bg-teal-600">
          주문 제출
        </button>
      </form>
      <a href="/dashboard" className="mt-4 inline-block text-accent hover:underline">대시보드로 돌아가기</a>
    </div>
  );
};

export default OrderForm;
