import React, { useState } from 'react';
import api from '../api';
import { formatUSD } from '../utils';
import { Line } from 'react-chartjs-2';
import { toast } from 'react-toastify';

const STRATEGIES = [
  { key: 'buy_hold', name: '🪙 단순 보유', desc: '시작 시 풀매수 후 보유 (벤치마크)' },
  { key: 'ma_crossover', name: '📈 이동평균 크로스', desc: '단기 MA가 장기 MA를 상향 돌파 시 매수, 하향 시 매도' },
  { key: 'rsi', name: '🎯 RSI 역추세', desc: 'RSI 과매도(30)에서 매수, 과매수(70)에서 매도' },
  { key: 'dca', name: '💰 DCA 적립식', desc: '일정 주기로 잔고를 분할 매수' },
];

const Backtest = () => {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [interval, setIntervalKey] = useState('1h');
  const [limit, setLimit] = useState(500);
  const [strategy, setStrategy] = useState('ma_crossover');
  const [initialBalance, setInitialBalance] = useState(100000);
  const [maFast, setMaFast] = useState(20);
  const [maSlow, setMaSlow] = useState(60);
  const [rsiPeriod, setRsiPeriod] = useState(14);
  const [rsiOversold, setRsiOversold] = useState(30);
  const [rsiOverbought, setRsiOverbought] = useState(70);
  const [dcaPeriod, setDcaPeriod] = useState(24);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleRun = async () => {
    setLoading(true);
    try {
      const { data } = await api.post('/backtest/run', {
        symbol, interval, limit, strategy,
        initial_balance: parseFloat(initialBalance),
        ma_fast: maFast, ma_slow: maSlow,
        rsi_period: rsiPeriod, rsi_oversold: rsiOversold, rsi_overbought: rsiOverbought,
        dca_period_candles: dcaPeriod,
      });
      setResult(data);
      toast.success('백테스트 완료!');
    } catch (e) {
      toast.error(e.response?.data?.detail || '백테스트 실패');
    } finally {
      setLoading(false);
    }
  };

  const chartData = result?.equity_curve ? {
    labels: result.equity_curve.map(p => new Date(p.time * 1000).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })),
    datasets: [{
      label: '자산',
      data: result.equity_curve.map(p => p.equity),
      borderColor: result.return_pct >= 0 ? '#3fb68b' : '#f0616d',
      backgroundColor: result.return_pct >= 0 ? 'rgba(63,182,139,0.1)' : 'rgba(240,97,109,0.1)',
      borderWidth: 2, pointRadius: 0, tension: 0.2, fill: true,
    }],
  } : null;

  const chartOpts = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false }, ticks: { color: '#484f58', font: { size: 9 }, maxTicksLimit: 8 } },
      y: { position: 'right', grid: { color: 'rgba(43,49,57,0.3)' }, ticks: { color: '#484f58', font: { size: 9 }, callback: v => '$' + v.toLocaleString() } },
    },
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 fade-in">
      <h2 className="text-xl font-bold text-white mb-6">🧪 전략 백테스팅</h2>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 설정 */}
        <div className="bg-dark-800 rounded-2xl border border-dark-600 p-5">
          <h3 className="text-sm font-semibold text-white mb-4">백테스트 설정</h3>

          <div className="space-y-4">
            <div>
              <label className="block text-muted text-[10px] mb-1.5">전략</label>
              <select value={strategy} onChange={(e) => setStrategy(e.target.value)}
                className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white text-sm focus:outline-none focus:border-accent">
                {STRATEGIES.map(s => <option key={s.key} value={s.key}>{s.name}</option>)}
              </select>
              <p className="text-dark-500 text-[10px] mt-1">{STRATEGIES.find(s => s.key === strategy)?.desc}</p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-muted text-[10px] mb-1.5">코인</label>
                <select value={symbol} onChange={(e) => setSymbol(e.target.value)}
                  className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white text-sm focus:outline-none focus:border-accent">
                  <option value="BTCUSDT">BTC</option>
                  <option value="ETHUSDT">ETH</option>
                  <option value="BNBUSDT">BNB</option>
                </select>
              </div>
              <div>
                <label className="block text-muted text-[10px] mb-1.5">시간</label>
                <select value={interval} onChange={(e) => setIntervalKey(e.target.value)}
                  className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white text-sm focus:outline-none focus:border-accent">
                  <option value="1h">1시간</option>
                  <option value="4h">4시간</option>
                  <option value="1d">1일</option>
                  <option value="1w">1주</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-muted text-[10px] mb-1.5">캔들 수</label>
                <input type="number" value={limit} onChange={(e) => setLimit(e.target.value)}
                  className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white text-sm font-mono focus:outline-none focus:border-accent" />
              </div>
              <div>
                <label className="block text-muted text-[10px] mb-1.5">초기 자금 ($)</label>
                <input type="number" value={initialBalance} onChange={(e) => setInitialBalance(e.target.value)}
                  className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white text-sm font-mono focus:outline-none focus:border-accent" />
              </div>
            </div>

            {strategy === 'ma_crossover' && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-muted text-[10px] mb-1.5">단기 MA</label>
                  <input type="number" value={maFast} onChange={(e) => setMaFast(parseInt(e.target.value))}
                    className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white text-sm font-mono focus:outline-none focus:border-accent" />
                </div>
                <div>
                  <label className="block text-muted text-[10px] mb-1.5">장기 MA</label>
                  <input type="number" value={maSlow} onChange={(e) => setMaSlow(parseInt(e.target.value))}
                    className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white text-sm font-mono focus:outline-none focus:border-accent" />
                </div>
              </div>
            )}

            {strategy === 'rsi' && (
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="block text-muted text-[10px] mb-1.5">기간</label>
                  <input type="number" value={rsiPeriod} onChange={(e) => setRsiPeriod(parseInt(e.target.value))}
                    className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white text-sm font-mono focus:outline-none focus:border-accent" />
                </div>
                <div>
                  <label className="block text-muted text-[10px] mb-1.5">과매도</label>
                  <input type="number" value={rsiOversold} onChange={(e) => setRsiOversold(parseFloat(e.target.value))}
                    className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white text-sm font-mono focus:outline-none focus:border-accent" />
                </div>
                <div>
                  <label className="block text-muted text-[10px] mb-1.5">과매수</label>
                  <input type="number" value={rsiOverbought} onChange={(e) => setRsiOverbought(parseFloat(e.target.value))}
                    className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white text-sm font-mono focus:outline-none focus:border-accent" />
                </div>
              </div>
            )}

            {strategy === 'dca' && (
              <div>
                <label className="block text-muted text-[10px] mb-1.5">매수 주기 (캔들)</label>
                <input type="number" value={dcaPeriod} onChange={(e) => setDcaPeriod(parseInt(e.target.value))}
                  className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white text-sm font-mono focus:outline-none focus:border-accent" />
              </div>
            )}

            <button onClick={handleRun} disabled={loading}
              className="w-full py-3 bg-accent text-white font-semibold rounded-xl hover:bg-accent-hover active:scale-[0.98] transition-all disabled:opacity-50">
              {loading ? '시뮬레이션 중...' : '백테스트 실행 🚀'}
            </button>
          </div>
        </div>

        {/* 결과 */}
        <div className="lg:col-span-2 space-y-4">
          {!result ? (
            <div className="bg-dark-800 rounded-2xl border border-dark-600 p-12 text-center">
              <div className="text-4xl mb-3">🧪</div>
              <p className="text-muted">왼쪽에서 전략을 설정하고 실행해보세요</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="bg-dark-800 rounded-2xl border border-dark-600 p-4">
                  <p className="text-muted text-[10px] mb-1">최종 자산</p>
                  <p className="text-lg font-bold text-white font-mono">{formatUSD(result.final_equity)}</p>
                </div>
                <div className="bg-dark-800 rounded-2xl border border-dark-600 p-4">
                  <p className="text-muted text-[10px] mb-1">수익률</p>
                  <p className={`text-lg font-bold font-mono ${result.return_pct >= 0 ? 'text-profit' : 'text-loss'}`}>
                    {result.return_pct >= 0 ? '+' : ''}{result.return_pct}%
                  </p>
                </div>
                <div className="bg-dark-800 rounded-2xl border border-dark-600 p-4">
                  <p className="text-muted text-[10px] mb-1">vs 단순 보유</p>
                  <p className={`text-lg font-bold font-mono ${result.outperformance >= 0 ? 'text-profit' : 'text-loss'}`}>
                    {result.outperformance >= 0 ? '+' : ''}{result.outperformance}%
                  </p>
                </div>
                <div className="bg-dark-800 rounded-2xl border border-dark-600 p-4">
                  <p className="text-muted text-[10px] mb-1">최대 낙폭</p>
                  <p className="text-lg font-bold text-loss font-mono">-{result.max_drawdown_pct}%</p>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="bg-dark-800 rounded-2xl border border-dark-600 p-3 text-center">
                  <p className="text-muted text-[10px]">거래 횟수</p>
                  <p className="text-base font-bold text-white">{result.trade_count}회</p>
                </div>
                <div className="bg-dark-800 rounded-2xl border border-dark-600 p-3 text-center">
                  <p className="text-muted text-[10px]">청산 거래</p>
                  <p className="text-base font-bold text-white">{result.closed_trades}회</p>
                </div>
                <div className="bg-dark-800 rounded-2xl border border-dark-600 p-3 text-center">
                  <p className="text-muted text-[10px]">승률</p>
                  <p className="text-base font-bold text-white">{result.win_rate}%</p>
                </div>
              </div>

              {chartData && (
                <div className="bg-dark-800 rounded-2xl border border-dark-600 p-5">
                  <h3 className="text-sm font-semibold text-white mb-3">📈 자산 곡선</h3>
                  <div className="h-64"><Line data={chartData} options={chartOpts} /></div>
                </div>
              )}

              {result.trades && result.trades.length > 0 && (
                <div className="bg-dark-800 rounded-2xl border border-dark-600 overflow-hidden">
                  <div className="px-5 py-3 border-b border-dark-600">
                    <h3 className="text-sm font-semibold text-white">최근 거래</h3>
                  </div>
                  <div className="max-h-64 overflow-y-auto">
                    <table className="w-full">
                      <thead className="sticky top-0 bg-dark-800">
                        <tr className="border-b border-dark-600">
                          <th className="px-4 py-2 text-left text-[10px] text-muted">시간</th>
                          <th className="px-4 py-2 text-left text-[10px] text-muted">구분</th>
                          <th className="px-4 py-2 text-right text-[10px] text-muted">가격</th>
                          <th className="px-4 py-2 text-right text-[10px] text-muted">수량</th>
                          <th className="px-4 py-2 text-right text-[10px] text-muted">손익</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-dark-600">
                        {result.trades.slice().reverse().map((t, i) => (
                          <tr key={i}>
                            <td className="px-4 py-2 text-dark-400 text-[10px]">{new Date(t.time * 1000).toLocaleDateString('ko-KR')}</td>
                            <td className="px-4 py-2"><span className={`text-[10px] font-bold ${t.side === 'BUY' ? 'text-profit' : 'text-loss'}`}>{t.side === 'BUY' ? '매수' : '매도'}</span></td>
                            <td className="px-4 py-2 text-right text-white text-[10px] font-mono">{formatUSD(t.price)}</td>
                            <td className="px-4 py-2 text-right text-muted text-[10px] font-mono">{t.qty.toFixed(4)}</td>
                            <td className={`px-4 py-2 text-right text-[10px] font-mono ${t.pnl > 0 ? 'text-profit' : t.pnl < 0 ? 'text-loss' : 'text-muted'}`}>
                              {t.pnl != null ? (t.pnl >= 0 ? '+' : '') + formatUSD(t.pnl) : '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Backtest;
