import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../api';
import { formatUSD, toNum, getWsUrl } from '../utils';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'];
const ORDER_TYPES = [
  { key: 'MARKET', label: 'Market' },
  { key: 'LIMIT', label: 'Limit' },
  { key: 'STOP_LOSS_LIMIT', label: 'Stop-Loss' },
  { key: 'TAKE_PROFIT_LIMIT', label: 'Take-Profit' },
];

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
    api.get('/account').then(({ data }) => {
      setBalance(toNum(data.balance));
      setFeeInfo(data.fee_info);
    }).catch(() => {});
    api.get('/account/symbol-rules').then(({ data }) => setSymbolRules(data)).catch(() => {});
  }, []);

  const connectWs = useCallback(() => {
    wsRef.current?.close();
    const ws = new WebSocket(getWsUrl(`/ws/prices/${symbol}`));
    wsRef.current = ws;
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.price) setLivePrice(parseFloat(data.price));
    };
    ws.onerror = () => ws.close();
  }, [symbol]);

  useEffect(() => {
    connectWs();
    return () => wsRef.current?.close();
  }, [connectWs]);

  const rules = symbolRules[symbol] || {};
  const needsPrice = orderType !== 'MARKET';
  const needsStopPrice = orderType === 'STOP_LOSS_LIMIT' || orderType === 'TAKE_PROFIT_LIMIT';

  const effectivePrice = needsPrice ? (parseFloat(price) || 0) : (livePrice || 0);
  const qty = parseFloat(quantity) || 0;
  const notional = effectivePrice * qty;

  // Fee calculation (mirror backend)
  const feeRate = feeInfo
    ? parseFloat(orderType === 'MARKET' ? feeInfo.taker_fee : feeInfo.maker_fee) / 100
    : 0.001;
  const fee = notional * feeRate;
  const total = side === 'BUY' ? notional + fee : notional - fee;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (qty <= 0) { toast.error('Enter a valid quantity'); return; }
    if (needsPrice && effectivePrice <= 0) { toast.error('Enter a valid price'); return; }
    if (needsStopPrice && (!stopPrice || parseFloat(stopPrice) <= 0)) { toast.error('Enter a valid stop price'); return; }

    setLoading(true);
    try {
      const payload = {
        symbol, side, order_type: orderType, quantity: qty,
      };
      if (needsPrice) payload.price = parseFloat(price);
      if (needsStopPrice) payload.stop_price = parseFloat(stopPrice);

      const { data } = await api.post('/orders', payload);
      const fillInfo = data.filled_price ? ` @ ${formatUSD(data.filled_price)}` : '';
      const feeInfo2 = data.commission > 0 ? ` (fee: ${formatUSD(data.commission)})` : '';
      toast.success(`${side} ${data.order_status}${fillInfo}${feeInfo2}`);
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Order failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div className="max-w-md mx-auto">
        {/* Live price + balance bar */}
        <div className="bg-dark-800 rounded-xl border border-dark-600 p-4 mb-4 flex items-center justify-between fade-in">
          <div>
            <p className="text-muted text-[10px] uppercase tracking-wider">{symbol}</p>
            <p className="text-xl font-bold text-white font-mono mt-0.5">
              {livePrice ? formatUSD(livePrice) : <span className="skeleton inline-block h-6 w-28" />}
            </p>
          </div>
          <div className="text-right">
            <p className="text-muted text-[10px] uppercase tracking-wider">Balance</p>
            <p className="text-sm font-mono text-white mt-0.5">{balance !== null ? formatUSD(balance) : '-'}</p>
            {feeInfo && (
              <p className="text-[9px] text-dark-400 mt-0.5">
                {feeInfo.tier} &middot; Maker {feeInfo.maker_fee} / Taker {feeInfo.taker_fee}
                {feeInfo.bnb_discount && ' (BNB -25%)'}
              </p>
            )}
          </div>
        </div>

        <div className="bg-dark-800 rounded-xl border border-dark-600 overflow-hidden fade-in">
          {/* BUY/SELL */}
          <div className="grid grid-cols-2">
            {['BUY', 'SELL'].map((s) => (
              <button key={s} type="button" onClick={() => setSide(s)}
                className={`py-3.5 text-sm font-semibold uppercase tracking-wider transition-all ${
                  side === s
                    ? s === 'BUY' ? 'bg-profit text-white' : 'bg-loss text-white'
                    : 'bg-dark-700 text-muted hover:text-white'
                }`}>{s}</button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="p-5 space-y-4">
            {/* Symbol */}
            <div>
              <label className="block text-muted text-[10px] font-medium mb-2 uppercase tracking-wider">Pair</label>
              <div className="grid grid-cols-3 gap-2">
                {SYMBOLS.map((s) => (
                  <button key={s} type="button" onClick={() => { setSymbol(s); setLivePrice(null); }}
                    className={`py-2 rounded-lg text-sm font-medium transition-all ${
                      symbol === s
                        ? 'bg-accent text-dark-900 shadow-lg shadow-accent/20'
                        : 'bg-dark-700 text-muted hover:text-white border border-dark-600'
                    }`}>
                    {s.replace('USDT', '')}<span className="text-[10px] opacity-60">/USDT</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Order type */}
            <div>
              <label className="block text-muted text-[10px] font-medium mb-2 uppercase tracking-wider">Type</label>
              <div className="grid grid-cols-2 gap-2">
                {ORDER_TYPES.map(({ key, label }) => (
                  <button key={key} type="button" onClick={() => setOrderType(key)}
                    className={`py-2 rounded-lg text-xs font-medium transition-colors ${
                      orderType === key
                        ? 'bg-dark-600 text-white ring-1 ring-dark-500'
                        : 'bg-dark-700 text-muted hover:text-white border border-dark-600'
                    }`}>{label}</button>
                ))}
              </div>
            </div>

            {/* Stop Price (for stop/TP orders) */}
            {needsStopPrice && (
              <div>
                <label className="block text-muted text-[10px] font-medium mb-2 uppercase tracking-wider">
                  {orderType === 'STOP_LOSS_LIMIT' ? 'Stop Price' : 'Trigger Price'}
                  <span className="text-dark-500 normal-case ml-1">(trigger)</span>
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-dark-500">$</span>
                  <input type="number" step="any" value={stopPrice}
                    onChange={(e) => setStopPrice(e.target.value)}
                    className="w-full pl-8 pr-4 py-3 bg-dark-700 border border-dark-600 rounded-lg text-white font-mono placeholder-dark-500 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors"
                    placeholder={rules.tickSize ? `Step: ${rules.tickSize}` : '0.00'} />
                </div>
              </div>
            )}

            {/* Price (for limit/stop orders) */}
            {needsPrice && (
              <div>
                <label className="block text-muted text-[10px] font-medium mb-2 uppercase tracking-wider">
                  Limit Price
                  <span className="text-dark-500 normal-case ml-1">(USDT)</span>
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-dark-500">$</span>
                  <input type="number" step="any" value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    className="w-full pl-8 pr-4 py-3 bg-dark-700 border border-dark-600 rounded-lg text-white font-mono placeholder-dark-500 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors"
                    placeholder={rules.tickSize ? `Tick: ${rules.tickSize}` : '0.00'} />
                </div>
              </div>
            )}

            {/* Quantity */}
            <div>
              <label className="block text-muted text-[10px] font-medium mb-2 uppercase tracking-wider">
                Amount
                <span className="text-dark-500 normal-case ml-1">
                  ({symbol.replace('USDT', '')}{rules.minQty ? ` / min: ${rules.minQty}` : ''})
                </span>
              </label>
              <input type="number" step={rules.stepSize || 'any'} min={rules.minQty || undefined}
                value={quantity} onChange={(e) => setQuantity(e.target.value)}
                className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-lg text-white font-mono placeholder-dark-500 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors"
                placeholder={rules.stepSize ? `Step: ${rules.stepSize}` : '0.00'} />
              {/* Quick % buttons */}
              {balance !== null && side === 'BUY' && effectivePrice > 0 && (
                <div className="flex space-x-2 mt-2">
                  {[25, 50, 75, 100].map((pct) => {
                    const maxQty = (balance * (pct / 100)) / (effectivePrice * (1 + feeRate));
                    const step = parseFloat(rules.stepSize || '0.000001');
                    const rounded = Math.floor(maxQty / step) * step;
                    return (
                      <button key={pct} type="button" onClick={() => setQuantity(rounded.toFixed(6))}
                        className="flex-1 py-1 text-[10px] font-medium bg-dark-700 text-muted hover:text-white rounded border border-dark-600 transition-colors">
                        {pct}%
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Cost summary */}
            {qty > 0 && effectivePrice > 0 && (
              <div className="bg-dark-900 rounded-lg p-3 space-y-1.5 text-xs fade-in">
                <div className="flex justify-between">
                  <span className="text-muted">Price</span>
                  <span className="text-white font-mono">
                    {orderType === 'MARKET' ? '~' : ''}{formatUSD(effectivePrice)}
                    {orderType === 'MARKET' && <span className="text-dark-500 ml-1">(+slippage)</span>}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Notional</span>
                  <span className="text-white font-mono">{formatUSD(notional)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">
                    Fee ({(feeRate * 100).toFixed(3)}%
                    {orderType !== 'MARKET' ? ' maker' : ' taker'}
                    {feeInfo?.bnb_discount ? ' BNB' : ''})
                  </span>
                  <span className="text-white font-mono">{formatUSD(fee)}</span>
                </div>
                {notional < parseFloat(rules.minNotional || '0') && (
                  <div className="text-loss text-[10px] pt-1">
                    Min order value: ${rules.minNotional} USDT
                  </div>
                )}
                <div className="border-t border-dark-600 pt-1.5 flex justify-between font-semibold">
                  <span className="text-white">{side === 'BUY' ? 'Total Cost' : 'You Receive'}</span>
                  <span className={`font-mono ${side === 'BUY' ? 'text-profit' : 'text-loss'}`}>
                    {formatUSD(total)}
                  </span>
                </div>
              </div>
            )}

            <button type="submit" disabled={loading || qty <= 0}
              className={`w-full py-3.5 font-semibold rounded-lg transition-all active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed ${
                side === 'BUY'
                  ? 'bg-profit text-white hover:shadow-lg hover:shadow-profit/20'
                  : 'bg-loss text-white hover:shadow-lg hover:shadow-loss/20'
              }`}>
              {loading ? (
                <span className="flex items-center justify-center space-x-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                  <span>Processing...</span>
                </span>
              ) : `${side} ${symbol.replace('USDT', '')}`}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default OrderForm;
