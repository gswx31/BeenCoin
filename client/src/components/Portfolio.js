import React, { useState, useEffect } from 'react';
import api from '../api';
import { formatUSD, formatQty, toNum, signedFormat, formatPercent } from '../utils';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';

const Portfolio = () => {
  const [positions, setPositions] = useState([]);
  const [account, setAccount] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/account').then(({ data }) => { setAccount(data); setPositions(data.positions || []); })
      .catch(() => toast.error('포트폴리오를 불러올 수 없어요'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">{[1,2,3,4].map(i => <div key={i} className="skeleton h-20 rounded-2xl" />)}</div>
      <div className="skeleton h-64 rounded-2xl" />
    </div>
  );

  const totalUnrealized = positions.reduce((sum, p) => sum + toNum(p.unrealized_profit), 0);
  const totalValue = positions.reduce((sum, p) => sum + toNum(p.current_value), 0);
  const balance = toNum(account?.balance);
  const totalAssets = balance + totalValue;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <div className="bg-dark-800 rounded-2xl p-4 border border-dark-600 fade-in">
          <p className="text-muted text-xs mb-1">📊 포트폴리오</p>
          <p className="text-lg font-bold text-white font-mono">{formatUSD(totalValue)}</p>
        </div>
        <div className="bg-dark-800 rounded-2xl p-4 border border-dark-600 fade-in">
          <p className="text-muted text-xs mb-1">💫 미실현 손익</p>
          <p className={`text-lg font-bold font-mono ${totalUnrealized >= 0 ? 'text-profit' : 'text-loss'}`}>{signedFormat(totalUnrealized)}</p>
        </div>
        <div className="bg-dark-800 rounded-2xl p-4 border border-dark-600 fade-in">
          <p className="text-muted text-xs mb-1">💵 현금 잔고</p>
          <p className="text-lg font-bold text-white font-mono">{formatUSD(balance)}</p>
        </div>
        <div className="bg-dark-800 rounded-2xl p-4 border border-dark-600 fade-in">
          <p className="text-muted text-xs mb-1">🪙 보유 코인</p>
          <p className="text-lg font-bold text-white">{positions.length}개</p>
        </div>
      </div>

      {positions.length > 0 && totalAssets > 0 && (
        <div className="bg-dark-800 rounded-2xl border border-dark-600 p-5 mb-6 fade-in">
          <h3 className="text-sm font-semibold text-white mb-3">자산 배분</h3>
          <div className="flex rounded-full h-3 overflow-hidden bg-dark-700">
            {positions.map((pos, i) => {
              const pct = (toNum(pos.current_value) / totalAssets) * 100;
              const colors = ['bg-accent', 'bg-profit', 'bg-lavender', 'bg-coral'];
              return <div key={i} className={`${colors[i % colors.length]} transition-all`} style={{ width: `${pct}%` }} title={`${pos.symbol}: ${pct.toFixed(1)}%`} />;
            })}
            <div className="bg-dark-500 transition-all" style={{ width: `${(balance / totalAssets) * 100}%` }} />
          </div>
          <div className="flex flex-wrap gap-4 mt-3">
            {positions.map((pos, i) => {
              const pct = (toNum(pos.current_value) / totalAssets) * 100;
              const dots = ['bg-accent', 'bg-profit', 'bg-lavender', 'bg-coral'];
              return <div key={i} className="flex items-center space-x-1.5"><span className={`w-2 h-2 rounded-full ${dots[i % dots.length]}`} /><span className="text-xs text-muted">{pos.symbol.replace('USDT', '')} {pct.toFixed(1)}%</span></div>;
            })}
            <div className="flex items-center space-x-1.5"><span className="w-2 h-2 rounded-full bg-dark-500" /><span className="text-xs text-muted">현금 {((balance / totalAssets) * 100).toFixed(1)}%</span></div>
          </div>
        </div>
      )}

      {positions.length === 0 ? (
        <div className="bg-dark-800 rounded-2xl border border-dark-600 p-12 text-center fade-in">
          <div className="text-4xl mb-4">🌱</div>
          <p className="text-muted mb-1">아직 보유 코인이 없어요</p>
          <p className="text-dark-500 text-sm mb-4">첫 거래를 시작해보세요!</p>
          <button onClick={() => navigate('/order')} className="px-6 py-2.5 bg-accent text-white font-semibold rounded-2xl hover:bg-accent-hover active:scale-[0.98] transition-all text-sm">거래 시작하기</button>
        </div>
      ) : (
        <div className="bg-dark-800 rounded-2xl border border-dark-600 overflow-hidden fade-in">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-dark-600">
                  <th className="px-5 py-3 text-left text-[11px] font-medium text-muted">코인</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted">수량</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted">평균가</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted">평가금액</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted">손익</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted">비중</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-600">
                {positions.map((pos, i) => {
                  const pnl = toNum(pos.unrealized_profit);
                  const avgPrice = toNum(pos.average_price);
                  const curVal = toNum(pos.current_value);
                  const qty2 = toNum(pos.quantity);
                  const curPrice = qty2 > 0 ? curVal / qty2 : 0;
                  const pnlPct = avgPrice > 0 ? ((curPrice - avgPrice) / avgPrice) * 100 : 0;
                  const alloc = totalAssets > 0 ? (curVal / totalAssets * 100) : 0;
                  return (
                    <tr key={i} className="hover:bg-dark-700/50 transition-colors">
                      <td className="px-5 py-3.5"><div className="flex items-center space-x-3"><div className="w-8 h-8 bg-accent/15 rounded-xl flex items-center justify-center"><span className="text-accent text-[10px] font-bold">{pos.symbol.replace('USDT', '').slice(0, 3)}</span></div><div><p className="text-white text-sm font-medium">{pos.symbol.replace('USDT', '')}</p><p className="text-muted text-[10px]">/ USDT</p></div></div></td>
                      <td className="px-5 py-3.5 text-right text-white text-sm font-mono">{formatQty(pos.quantity, 4)}</td>
                      <td className="px-5 py-3.5 text-right text-white text-sm font-mono">{formatUSD(pos.average_price)}</td>
                      <td className="px-5 py-3.5 text-right text-white text-sm font-mono">{formatUSD(pos.current_value)}</td>
                      <td className="px-5 py-3.5 text-right">
                        <p className={`text-sm font-mono font-medium ${pnl >= 0 ? 'text-profit' : 'text-loss'}`}>{signedFormat(pos.unrealized_profit)}</p>
                        <p className={`text-[10px] font-mono ${pnl >= 0 ? 'text-profit' : 'text-loss'} opacity-70`}>{pnlPct >= 0 ? '+' : ''}{formatPercent(pnlPct)}</p>
                      </td>
                      <td className="px-5 py-3.5 text-right text-muted text-sm font-mono">{alloc.toFixed(1)}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default Portfolio;
