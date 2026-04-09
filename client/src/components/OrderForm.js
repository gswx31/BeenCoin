import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../api';
import { formatUSD, toNum, getWsUrl } from '../utils';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'];
const ORDER_TYPES = [
  { key: 'MARKET', label: '시장가' },
  { key: 'LIMIT', label: '지정가' },
  { key: 'STOP_LOSS_LIMIT', label: '손절매' },
  { key: 'TAKE_PROFIT_LIMIT', label: '익절매' },
];
const FEE_RATE_DEFAULT = 0.001;

const OrderForm = () => {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [side, setSide] = useState('BUY');
  const [orderType, setOrderType] = useState('MARKET');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [stopPrice, setStopPrice] = useState('');
  const [loading, setLoading] = useState(false);
  const [livePrice, setLivePrice] = useState(null);
  const [balance, setBalance] = useState(null);
  const [feeInfo, setFeeInfo] = useState(null);
  const [symbolRules, setSymbolRules] = useState({});
  const navigate = useNavigate();
  const wsRef = useRef(null);

  useEffect(() => {
    api.get('/account').then(({ data }) => { setBalance(toNum(data.balance)); setFeeInfo(data.fee_info); }).catch(() => {});
    api.get('/account/symbol-rules').then(({ data }) => setSymbolRules(data)).catch(() => {});
  }, []);

  const connectWs = useCallback(() => {
    wsRef.current?.close();
    const ws = new WebSocket(getWsUrl(`/ws/prices/${symbol}`));
    wsRef.current = ws;
    ws.onmessage = (e) => { const d = JSON.parse(e.data); if (d.price) setLivePrice(parseFloat(d.price)); };
    ws.onerror = () => ws.close();
  }, [symbol]);

  useEffect(() => { connectWs(); return () => wsRef.current?.close(); }, [connectWs]);

  const rules = symbolRules[symbol] || {};
  const needsPrice = orderType !== 'MARKET';
  const needsStopPrice = orderType === 'STOP_LOSS_LIMIT' || orderType === 'TAKE_PROFIT_LIMIT';
  const effectivePrice = needsPrice ? (parseFloat(price) || 0) : (livePrice || 0);
  const qty = parseFloat(quantity) || 0;
  const notional = effectivePrice * qty;
  const feeRate = feeInfo ? parseFloat(orderType === 'MARKET' ? feeInfo.taker_fee : feeInfo.maker_fee) / 100 : FEE_RATE_DEFAULT;
  const fee = notional * feeRate;
  const total = side === 'BUY' ? notional + fee : notional - fee;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (qty <= 0) { toast.error('수량을 입력해주세요'); return; }
    if (needsPrice && effectivePrice <= 0) { toast.error('가격을 입력해주세요'); return; }
    if (needsStopPrice && (!stopPrice || parseFloat(stopPrice) <= 0)) { toast.error('트리거 가격을 입력해주세요'); return; }
    setLoading(true);
    try {
      const payload = { symbol, side, order_type: orderType, quantity: qty };
      if (needsPrice) payload.price = parseFloat(price);
      if (needsStopPrice) payload.stop_price = parseFloat(stopPrice);
      const { data } = await api.post('/orders', payload);
      const fillInfo = data.filled_price ? ` @ ${formatUSD(data.filled_price)}` : '';
      toast.success(`${side === 'BUY' ? '매수' : '매도'} ${data.order_status === 'FILLED' ? '체결 완료' : '주문 접수'}${fillInfo} ✨`);
      navigate('/dashboard');
    } catch (error) { toast.error(error.response?.data?.detail || '주문에 실패했어요 😢'); }
    finally { setLoading(false); }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div className="max-w-md mx-auto">
        <div className="bg-dark-800 rounded-2xl border border-dark-600 p-4 mb-4 flex items-center justify-between fade-in">
          <div>
            <p className="text-muted text-[10px]">{symbol} 현재가</p>
            <p className="text-xl font-bold text-white font-mono mt-0.5">
              {livePrice ? formatUSD(livePrice) : <span className="skeleton inline-block h-6 w-28" />}
            </p>
          </div>
          {balance !== null && (
            <div className="text-right">
              <p className="text-muted text-[10px]">내 잔고</p>
              <p className="text-sm font-mono text-white mt-0.5">{formatUSD(balance)}</p>
              {feeInfo && <p className="text-[9px] text-dark-400 mt-0.5">{feeInfo.tier} · 수수료 {feeInfo.taker_fee}</p>}
            </div>
          )}
        </div>

        <div className="bg-dark-800 rounded-2xl border border-dark-600 overflow-hidden fade-in">
          <div className="grid grid-cols-2">
            {['BUY', 'SELL'].map((s) => (
              <button key={s} type="button" onClick={() => setSide(s)}
                className={`py-3.5 text-sm font-semibold transition-all ${
                  side === s ? s === 'BUY' ? 'bg-profit text-white' : 'bg-loss text-white' : 'bg-dark-700 text-muted hover:text-white'
                }`}>{s === 'BUY' ? '매수' : '매도'}</button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="p-5 space-y-4">
            <div>
              <label className="block text-muted text-[10px] font-medium mb-2">코인 선택</label>
              <div className="grid grid-cols-3 gap-2">
                {SYMBOLS.map((s) => (
                  <button key={s} type="button" onClick={() => { setSymbol(s); setLivePrice(null); }}
                    className={`py-2 rounded-xl text-sm font-medium transition-all ${
                      symbol === s ? 'bg-accent text-white shadow-lg shadow-accent/20' : 'bg-dark-700 text-muted hover:text-white border border-dark-600'
                    }`}>{s.replace('USDT', '')}<span className="text-[10px] opacity-60">/USDT</span></button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-muted text-[10px] font-medium mb-2">주문 유형</label>
              <div className="grid grid-cols-2 gap-2">
                {ORDER_TYPES.map(({ key, label }) => (
                  <button key={key} type="button" onClick={() => setOrderType(key)}
                    className={`py-2 rounded-xl text-xs font-medium transition-colors ${
                      orderType === key ? 'bg-dark-600 text-white ring-1 ring-dark-500' : 'bg-dark-700 text-muted hover:text-white border border-dark-600'
                    }`}>{label}</button>
                ))}
              </div>
            </div>

            {needsStopPrice && (
              <div>
                <label className="block text-muted text-[10px] font-medium mb-2">
                  {orderType === 'STOP_LOSS_LIMIT' ? '손절 트리거 가격' : '익절 트리거 가격'}
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-dark-500">$</span>
                  <input type="number" step="any" value={stopPrice} onChange={(e) => setStopPrice(e.target.value)}
                    className="w-full pl-8 pr-4 py-3 bg-dark-700 border border-dark-600 rounded-2xl text-white font-mono placeholder-dark-500 focus:outline-none focus:border-accent transition-all" placeholder="0.00" />
                </div>
              </div>
            )}

            {needsPrice && (
              <div>
                <label className="block text-muted text-[10px] font-medium mb-2">지정 가격 (USDT)</label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-dark-500">$</span>
                  <input type="number" step="any" value={price} onChange={(e) => setPrice(e.target.value)}
                    className="w-full pl-8 pr-4 py-3 bg-dark-700 border border-dark-600 rounded-2xl text-white font-mono placeholder-dark-500 focus:outline-none focus:border-accent transition-all" placeholder="0.00" />
                </div>
              </div>
            )}

            <div>
              <label className="block text-muted text-[10px] font-medium mb-2">
                수량 <span className="text-dark-500">({symbol.replace('USDT', '')}{rules.minQty ? ` / 최소: ${rules.minQty}` : ''})</span>
              </label>
              <input type="number" step={rules.stepSize || 'any'} value={quantity} onChange={(e) => setQuantity(e.target.value)}
                className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-2xl text-white font-mono placeholder-dark-500 focus:outline-none focus:border-accent transition-all" placeholder="0.00" />
              {balance !== null && side === 'BUY' && effectivePrice > 0 && (
                <div className="flex space-x-2 mt-2">
                  {[25, 50, 75, 100].map((pct) => {
                    const maxQty = (balance * (pct / 100)) / (effectivePrice * (1 + feeRate));
                    const step = parseFloat(rules.stepSize || '0.000001');
                    return (
                      <button key={pct} type="button" onClick={() => setQuantity((Math.floor(maxQty / step) * step).toFixed(6))}
                        className="flex-1 py-1 text-[10px] font-medium bg-dark-700 text-muted hover:text-white rounded-lg border border-dark-600 transition-colors">{pct}%</button>
                    );
                  })}
                </div>
              )}
            </div>

            {qty > 0 && effectivePrice > 0 && (
              <div className="bg-dark-900 rounded-2xl p-3 space-y-1.5 text-xs fade-in">
                <div className="flex justify-between"><span className="text-muted">예상 가격</span><span className="text-white font-mono">{orderType === 'MARKET' ? '≈' : ''}{formatUSD(effectivePrice)}</span></div>
                <div className="flex justify-between"><span className="text-muted">주문 금액</span><span className="text-white font-mono">{formatUSD(notional)}</span></div>
                <div className="flex justify-between"><span className="text-muted">수수료 ({(feeRate * 100).toFixed(3)}%)</span><span className="text-white font-mono">{formatUSD(fee)}</span></div>
                {notional < parseFloat(rules.minNotional || '0') && <div className="text-loss text-[10px] pt-1">⚠️ 최소 주문 금액: ${rules.minNotional}</div>}
                <div className="border-t border-dark-600 pt-1.5 flex justify-between font-semibold">
                  <span className="text-white">{side === 'BUY' ? '총 필요 금액' : '받을 금액'}</span>
                  <span className={`font-mono ${side === 'BUY' ? 'text-profit' : 'text-loss'}`}>{formatUSD(total)}</span>
                </div>
              </div>
            )}

            <button type="submit" disabled={loading || qty <= 0}
              className={`w-full py-3.5 font-semibold rounded-2xl transition-all active:scale-[0.98] disabled:opacity-40 ${
                side === 'BUY' ? 'bg-profit text-white hover:shadow-lg hover:shadow-profit/20' : 'bg-loss text-white hover:shadow-lg hover:shadow-loss/20'
              }`}>{loading ? '처리중...' : `${side === 'BUY' ? '매수' : '매도'} ${symbol.replace('USDT', '')}`}</button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default OrderForm;
