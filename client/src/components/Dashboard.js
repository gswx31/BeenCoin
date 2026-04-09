import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import { formatUSD, formatPercent, toNum, signedFormat } from '../utils';
import TradingChart from './TradingChart';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'];

const StatCard = ({ icon, label, value, sub, color = 'text-white' }) => (
  <div className="bg-dark-800 rounded-2xl p-5 border border-dark-600 fade-in">
    <div className="flex items-center space-x-2 mb-1">
      <span className="text-sm">{icon}</span>
      <p className="text-muted text-xs font-medium">{label}</p>
    </div>
    <p className={`text-xl font-bold font-mono ${color}`}>{value}</p>
    {sub && <p className={`text-[11px] mt-1 ${color} opacity-70`}>{sub}</p>}
  </div>
);

const Dashboard = () => {
  const [account, setAccount] = useState(null);
  const [currentPrice, setCurrentPrice] = useState(null);
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT');
  const [recentOrders, setRecentOrders] = useState([]);
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    try {
      const [accRes, ordRes] = await Promise.all([api.get('/account'), api.get('/orders')]);
      setAccount(accRes.data);
      setRecentOrders(ordRes.data.slice(0, 5));
    } catch { toast.error('데이터를 불러올 수 없어요'); }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handlePriceUpdate = useCallback((price) => setCurrentPrice(price), []);

  if (!account) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">{[1,2,3,4].map(i => <div key={i} className="skeleton h-24 rounded-2xl" />)}</div>
        <div className="skeleton h-96 w-full rounded-2xl" />
      </div>
    );
  }

  const profit = toNum(account.total_profit);
  const rate = toNum(account.profit_rate);
  const positions = account.positions || [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <StatCard icon="💰" label="사용 가능 잔고" value={formatUSD(account.balance)} />
        <StatCard icon={profit >= 0 ? "📈" : "📉"} label="총 손익"
          value={signedFormat(account.total_profit)} color={profit >= 0 ? 'text-profit' : 'text-loss'} />
        <StatCard icon="🎯" label="수익률"
          value={signedFormat(account.profit_rate, formatPercent)} color={rate >= 0 ? 'text-profit' : 'text-loss'} />
        <StatCard icon="🏦" label="총 자산"
          value={formatUSD(account.total_value)} sub={`${positions.length}개 포지션 보유중`} />
      </div>

      <div className="bg-dark-800 rounded-2xl border border-dark-600 p-5 mb-6 fade-in">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-3">
            <div className="flex space-x-1">
              {SYMBOLS.map((s) => (
                <button key={s} onClick={() => setSelectedSymbol(s)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                    selectedSymbol === s ? 'bg-accent text-white' : 'text-muted hover:text-white'
                  }`}>{s.replace('USDT', '')}</button>
              ))}
            </div>
            {currentPrice !== null && (
              <span className="text-xl font-bold text-white font-mono">{formatUSD(currentPrice)}</span>
            )}
          </div>
        </div>
        <TradingChart symbol={selectedSymbol} onPriceUpdate={handlePriceUpdate} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-dark-800 rounded-2xl border border-dark-600 fade-in">
          <div className="flex items-center justify-between px-5 py-4 border-b border-dark-600">
            <h3 className="text-sm font-semibold text-white">📊 보유 포지션</h3>
            <button onClick={() => navigate('/portfolio')} className="text-xs text-accent hover:text-accent-hover">전체보기</button>
          </div>
          {positions.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-muted text-sm mb-3">아직 보유 포지션이 없어요</p>
              <button onClick={() => navigate('/order')} className="text-xs text-accent hover:text-accent-hover font-medium">첫 거래 시작하기 →</button>
            </div>
          ) : (
            <div className="divide-y divide-dark-600">
              {positions.slice(0, 5).map((pos, i) => {
                const pnl = toNum(pos.unrealized_profit);
                return (
                  <div key={i} className="flex items-center justify-between px-5 py-3 hover:bg-dark-700 transition-colors">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-accent/15 rounded-xl flex items-center justify-center">
                        <span className="text-accent text-xs font-bold">{pos.symbol.replace('USDT', '').slice(0, 3)}</span>
                      </div>
                      <div>
                        <p className="text-white text-sm font-medium">{pos.symbol}</p>
                        <p className="text-muted text-xs font-mono">{toNum(pos.quantity).toFixed(4)}개</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-white text-sm font-mono">{formatUSD(pos.current_value)}</p>
                      <p className={`text-xs font-mono ${pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                        {pnl >= 0 ? '+' : ''}{formatUSD(pos.unrealized_profit)}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="bg-dark-800 rounded-2xl border border-dark-600 fade-in">
          <div className="flex items-center justify-between px-5 py-4 border-b border-dark-600">
            <h3 className="text-sm font-semibold text-white">📋 최근 주문</h3>
            <button onClick={() => navigate('/history')} className="text-xs text-accent hover:text-accent-hover">전체보기</button>
          </div>
          {recentOrders.length === 0 ? (
            <div className="p-8 text-center"><p className="text-muted text-sm">아직 주문 내역이 없어요</p></div>
          ) : (
            <div className="divide-y divide-dark-600">
              {recentOrders.map((order) => (
                <div key={order.id} className="flex items-center justify-between px-5 py-3 hover:bg-dark-700 transition-colors">
                  <div className="flex items-center space-x-3">
                    <span className={`px-2 py-0.5 rounded-lg text-[10px] font-bold ${
                      order.side === 'BUY' ? 'bg-profit-soft text-profit' : 'bg-loss-soft text-loss'
                    }`}>{order.side === 'BUY' ? '매수' : '매도'}</span>
                    <div>
                      <p className="text-white text-sm font-medium">{order.symbol}</p>
                      <p className="text-muted text-xs">{toNum(order.quantity).toFixed(4)}개</p>
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    order.order_status === 'FILLED' ? 'bg-profit-soft text-profit' :
                    order.order_status === 'CANCELLED' ? 'bg-dark-600 text-muted' :
                    'bg-accent-soft text-accent'
                  }`}>{
                    order.order_status === 'FILLED' ? '체결' :
                    order.order_status === 'CANCELLED' ? '취소됨' :
                    order.order_status === 'PENDING' ? '대기중' : order.order_status
                  }</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
