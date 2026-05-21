import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../api';
import { formatUSD, getWsUrl, toNum } from '../utils';
import { toast } from 'react-toastify';
import HelpTooltip from './HelpTooltip';

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'];
const LEVERAGE_OPTIONS = [1, 2, 3, 5, 10, 20, 50];

const Futures = () => {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [side, setSide] = useState('LONG');
  const [margin, setMargin] = useState('');
  const [leverage, setLeverage] = useState(10);
  const [livePrice, setLivePrice] = useState(null);
  const [balance, setBalance] = useState(0);
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(false);
  const wsRef = useRef(null);

  const fetchData = useCallback(async () => {
    try {
      const [acc, pos] = await Promise.all([
        api.get('/account'),
        api.get('/futures/positions'),
      ]);
      setBalance(toNum(acc.data.balance));
      setPositions(pos.data);
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 3000);
    return () => clearInterval(id);
  }, [fetchData]);

  const connectWs = useCallback(() => {
    wsRef.current?.close();
    const ws = new WebSocket(getWsUrl(`/ws/prices/${symbol}`));
    wsRef.current = ws;
    ws.onmessage = (e) => {
      const d = JSON.parse(e.data);
      if (d.price) setLivePrice(parseFloat(d.price));
    };
    ws.onerror = () => ws.close();
  }, [symbol]);

  useEffect(() => {
    connectWs();
    return () => wsRef.current?.close();
  }, [connectWs]);

  const marginNum = parseFloat(margin) || 0;
  const positionSize = marginNum * leverage;
  const liqPrice = livePrice && side === 'LONG'
    ? livePrice * (1 - 1/leverage + 0.005)
    : livePrice * (1 + 1/leverage - 0.005);
  const fee = positionSize * 0.0004;

  const handleOpen = async () => {
    if (marginNum <= 0) { toast.error('증거금을 입력해주세요'); return; }
    if (marginNum > balance) { toast.error('잔고가 부족해요'); return; }
    setLoading(true);
    try {
      const { data } = await api.post('/futures/open', { symbol, side, margin: marginNum, leverage });
      toast.success(`${side === 'LONG' ? '롱' : '숏'} ${leverage}배 진입! 청산가: ${formatUSD(data.liquidation_price)}`);
      setMargin('');
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || '진입 실패');
    } finally { setLoading(false); }
  };

  const handleClose = async (id) => {
    try {
      const { data } = await api.post(`/futures/close/${id}`);
      const sign = data.realized_pnl >= 0 ? '+' : '';
      toast.success(`청산 완료 (${sign}${formatUSD(data.realized_pnl)})`);
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || '청산 실패');
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 fade-in">
      {/* 경고 배너 */}
      <div className="bg-loss/10 border border-loss/30 rounded-2xl p-4 mb-6">
        <p className="text-loss text-sm font-bold mb-1">⚠️ 선물 거래는 위험해요</p>
        <p className="text-muted text-xs leading-relaxed">
          레버리지로 적은 돈으로 큰 수익이 가능하지만, 가격이 반대로 움직이면 <span className="text-loss font-semibold">증거금을 전부 잃을 수 있어요 (강제 청산)</span>.
          처음이라면 1~3배 레버리지로 연습해보세요.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 주문 폼 */}
        <div className="bg-dark-800 rounded-2xl border border-dark-600 overflow-hidden">
          <div className="bg-dark-900 p-4 flex items-center justify-between">
            <div>
              <p className="text-muted text-[10px]">{symbol} 현재가</p>
              <p className="text-white font-mono font-bold">{livePrice ? formatUSD(livePrice) : '...'}</p>
            </div>
            <div className="text-right">
              <p className="text-muted text-[10px]">잔고</p>
              <p className="text-white font-mono text-sm">{formatUSD(balance)}</p>
            </div>
          </div>

          <div className="grid grid-cols-2">
            <button onClick={() => setSide('LONG')}
              className={`py-3.5 text-sm font-semibold transition-all ${side === 'LONG' ? 'bg-profit text-white' : 'bg-dark-700 text-muted hover:text-white'}`}>
              🚀 LONG (상승)
            </button>
            <button onClick={() => setSide('SHORT')}
              className={`py-3.5 text-sm font-semibold transition-all ${side === 'SHORT' ? 'bg-loss text-white' : 'bg-dark-700 text-muted hover:text-white'}`}>
              📉 SHORT (하락)
            </button>
          </div>

          <div className="p-5 space-y-4">
            <div>
              <label className="block text-muted text-[10px] mb-2">코인</label>
              <div className="grid grid-cols-3 gap-2">
                {SYMBOLS.map(s => (
                  <button key={s} onClick={() => { setSymbol(s); setLivePrice(null); }}
                    className={`py-2 rounded-xl text-sm font-medium ${symbol === s ? 'bg-accent text-white' : 'bg-dark-700 text-muted'}`}>
                    {s.replace('USDT', '')}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="flex items-center text-muted text-[10px] mb-2">
                레버리지 <HelpTooltip text="레버리지가 높을수록 적은 돈으로 큰 포지션을 만들 수 있지만, 청산 위험도 커져요. 초보는 1~3배 권장." />
                <span className="ml-auto text-accent font-bold text-base">{leverage}배</span>
              </label>
              <div className="flex space-x-1">
                {LEVERAGE_OPTIONS.map(l => (
                  <button key={l} onClick={() => setLeverage(l)}
                    className={`flex-1 py-2 rounded-lg text-xs font-medium ${
                      leverage === l ? 'bg-accent text-white' :
                      l >= 20 ? 'bg-loss/20 text-loss' :
                      l >= 10 ? 'bg-accent/15 text-accent' :
                      'bg-dark-700 text-muted'
                    }`}>{l}x</button>
                ))}
              </div>
            </div>

            <div>
              <label className="flex items-center text-muted text-[10px] mb-2">
                증거금 (USDT)
                <HelpTooltip text="실제 거는 돈이에요. 포지션 크기 = 증거금 × 레버리지" />
              </label>
              <input type="number" value={margin} onChange={(e) => setMargin(e.target.value)}
                className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-xl text-white font-mono focus:outline-none focus:border-accent"
                placeholder="0.00" />
              <div className="flex space-x-2 mt-2">
                {[10, 25, 50, 100].map(pct => (
                  <button key={pct} onClick={() => setMargin((balance * pct / 100).toFixed(2))}
                    className="flex-1 py-1 text-[10px] bg-dark-700 text-muted hover:text-white rounded-lg">
                    {pct}%
                  </button>
                ))}
              </div>
            </div>

            {marginNum > 0 && livePrice && (
              <div className="bg-dark-900 rounded-xl p-3 space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-muted">포지션 크기</span>
                  <span className="text-white font-mono">{formatUSD(positionSize)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">진입 수수료</span>
                  <span className="text-white font-mono">{formatUSD(fee)}</span>
                </div>
                <div className="flex justify-between border-t border-dark-600 pt-1.5">
                  <span className="text-loss flex items-center">
                    청산 예상가
                    <HelpTooltip text="이 가격이 되면 증거금을 모두 잃고 자동으로 포지션이 종료돼요." />
                  </span>
                  <span className="text-loss font-mono font-bold">{formatUSD(liqPrice)}</span>
                </div>
              </div>
            )}

            <button onClick={handleOpen} disabled={loading || marginNum <= 0}
              className={`w-full py-3.5 font-semibold rounded-2xl transition-all active:scale-[0.98] disabled:opacity-40 ${
                side === 'LONG' ? 'bg-profit text-white' : 'bg-loss text-white'
              }`}>
              {loading ? '처리중...' : `${side === 'LONG' ? '롱' : '숏'} ${leverage}배 진입`}
            </button>
          </div>
        </div>

        {/* 보유 포지션 */}
        <div className="lg:col-span-2">
          <h3 className="text-white font-bold mb-3">💼 보유 포지션 ({positions.length})</h3>
          {positions.length === 0 ? (
            <div className="bg-dark-800 rounded-2xl border border-dark-600 p-12 text-center">
              <div className="text-4xl mb-3">📊</div>
              <p className="text-muted">보유 중인 선물 포지션이 없어요</p>
            </div>
          ) : (
            <div className="space-y-3">
              {positions.map(p => {
                const isProfit = p.unrealized_pnl >= 0;
                const distToLiq = Math.abs(p.current_price - p.liquidation_price) / p.current_price * 100;
                return (
                  <div key={p.id} className="bg-dark-800 rounded-2xl border border-dark-600 p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${p.side === 'LONG' ? 'bg-profit-soft text-profit' : 'bg-loss-soft text-loss'}`}>
                          {p.side} {p.leverage}x
                        </span>
                        <span className="text-white font-medium text-sm">{p.symbol}</span>
                      </div>
                      <button onClick={() => handleClose(p.id)}
                        className="px-3 py-1 bg-dark-600 text-white text-xs rounded-lg hover:bg-dark-500">
                        종료
                      </button>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                      <div>
                        <p className="text-muted text-[10px]">진입가</p>
                        <p className="text-white font-mono">{formatUSD(p.entry_price)}</p>
                      </div>
                      <div>
                        <p className="text-muted text-[10px]">현재가</p>
                        <p className="text-white font-mono">{formatUSD(p.current_price)}</p>
                      </div>
                      <div>
                        <p className="text-muted text-[10px]">증거금</p>
                        <p className="text-white font-mono">{formatUSD(p.margin)}</p>
                      </div>
                      <div>
                        <p className="text-muted text-[10px]">손익</p>
                        <p className={`font-mono font-bold ${isProfit ? 'text-profit' : 'text-loss'}`}>
                          {isProfit ? '+' : ''}{formatUSD(p.unrealized_pnl)} ({p.pnl_pct.toFixed(1)}%)
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 pt-3 border-t border-dark-600 flex items-center justify-between text-[10px]">
                      <span className="text-loss">청산가 {formatUSD(p.liquidation_price)}</span>
                      <span className={distToLiq < 5 ? 'text-loss font-bold' : 'text-muted'}>
                        청산까지 {distToLiq.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Futures;
