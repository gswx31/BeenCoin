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
    const fetch = async () => {
      try {
        const { data } = await api.get('/account');
        setAccount(data);
        setPositions(data.positions || []);
      } catch {
        toast.error('Failed to load portfolio');
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          {[1,2,3,4].map(i => <div key={i} className="skeleton h-20 rounded-xl" />)}
        </div>
        <div className="skeleton h-64 rounded-xl" />
      </div>
    );
  }

  const totalUnrealized = positions.reduce((sum, p) => sum + toNum(p.unrealized_profit), 0);
  const totalValue = positions.reduce((sum, p) => sum + toNum(p.current_value), 0);
  const balance = toNum(account?.balance);
  const totalAssets = balance + totalValue;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <div className="bg-dark-800 rounded-xl p-4 border border-dark-600 fade-in">
          <p className="text-muted text-xs uppercase tracking-wider mb-1">Portfolio Value</p>
          <p className="text-lg font-bold text-white font-mono">{formatUSD(totalValue)}</p>
        </div>
        <div className="bg-dark-800 rounded-xl p-4 border border-dark-600 fade-in">
          <p className="text-muted text-xs uppercase tracking-wider mb-1">Unrealized P&L</p>
          <p className={`text-lg font-bold font-mono ${totalUnrealized >= 0 ? 'text-profit' : 'text-loss'}`}>
            {signedFormat(totalUnrealized)}
          </p>
        </div>
        <div className="bg-dark-800 rounded-xl p-4 border border-dark-600 fade-in">
          <p className="text-muted text-xs uppercase tracking-wider mb-1">Cash Balance</p>
          <p className="text-lg font-bold text-white font-mono">{formatUSD(balance)}</p>
        </div>
        <div className="bg-dark-800 rounded-xl p-4 border border-dark-600 fade-in">
          <p className="text-muted text-xs uppercase tracking-wider mb-1">Positions</p>
          <p className="text-lg font-bold text-white">{positions.length}</p>
        </div>
      </div>

      {/* Allocation bar */}
      {positions.length > 0 && totalAssets > 0 && (
        <div className="bg-dark-800 rounded-xl border border-dark-600 p-5 mb-6 fade-in">
          <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-3">Allocation</h3>
          <div className="flex rounded-full h-3 overflow-hidden bg-dark-700">
            {positions.map((pos, i) => {
              const pct = (toNum(pos.current_value) / totalAssets) * 100;
              const colors = ['bg-accent', 'bg-profit', 'bg-[#7b61ff]', 'bg-[#f0b90b]'];
              return (
                <div
                  key={i}
                  className={`${colors[i % colors.length]} transition-all`}
                  style={{ width: `${pct}%` }}
                  title={`${pos.symbol}: ${pct.toFixed(1)}%`}
                />
              );
            })}
            <div
              className="bg-dark-500 transition-all"
              style={{ width: `${(balance / totalAssets) * 100}%` }}
              title={`Cash: ${((balance / totalAssets) * 100).toFixed(1)}%`}
            />
          </div>
          <div className="flex flex-wrap gap-4 mt-3">
            {positions.map((pos, i) => {
              const pct = (toNum(pos.current_value) / totalAssets) * 100;
              const dotColors = ['bg-accent', 'bg-profit', 'bg-[#7b61ff]', 'bg-[#f0b90b]'];
              return (
                <div key={i} className="flex items-center space-x-1.5">
                  <span className={`w-2 h-2 rounded-full ${dotColors[i % dotColors.length]}`} />
                  <span className="text-xs text-muted">{pos.symbol.replace('USDT', '')} {pct.toFixed(1)}%</span>
                </div>
              );
            })}
            <div className="flex items-center space-x-1.5">
              <span className="w-2 h-2 rounded-full bg-dark-500" />
              <span className="text-xs text-muted">Cash {((balance / totalAssets) * 100).toFixed(1)}%</span>
            </div>
          </div>
        </div>
      )}

      {/* Positions table */}
      {positions.length === 0 ? (
        <div className="bg-dark-800 rounded-xl border border-dark-600 p-12 text-center fade-in">
          <div className="w-16 h-16 bg-dark-700 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-dark-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 12H4M12 4v16" />
            </svg>
          </div>
          <p className="text-muted mb-1">No positions yet</p>
          <p className="text-dark-500 text-sm mb-4">Place your first trade to get started</p>
          <button
            onClick={() => navigate('/order')}
            className="px-6 py-2.5 bg-accent text-dark-900 font-semibold rounded-lg hover:bg-accent-hover active:scale-[0.98] transition-all text-sm"
          >
            Start Trading
          </button>
        </div>
      ) : (
        <div className="bg-dark-800 rounded-xl border border-dark-600 overflow-hidden fade-in">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-dark-600">
                  <th className="px-5 py-3 text-left text-[11px] font-medium text-muted uppercase tracking-wider">Asset</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted uppercase tracking-wider">Qty</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted uppercase tracking-wider">Avg. Price</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted uppercase tracking-wider">Value</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted uppercase tracking-wider">P&L</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted uppercase tracking-wider">Alloc.</th>
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
                      <td className="px-5 py-3.5">
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 bg-accent/15 rounded-full flex items-center justify-center flex-shrink-0">
                            <span className="text-accent text-[10px] font-bold">
                              {pos.symbol.replace('USDT', '').slice(0, 3)}
                            </span>
                          </div>
                          <div>
                            <p className="text-white text-sm font-medium">{pos.symbol.replace('USDT', '')}</p>
                            <p className="text-muted text-[10px]">/ USDT</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-right text-white text-sm font-mono">{formatQty(pos.quantity, 4)}</td>
                      <td className="px-5 py-3.5 text-right text-white text-sm font-mono">{formatUSD(pos.average_price)}</td>
                      <td className="px-5 py-3.5 text-right text-white text-sm font-mono">{formatUSD(pos.current_value)}</td>
                      <td className="px-5 py-3.5 text-right">
                        <p className={`text-sm font-mono font-medium ${pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                          {signedFormat(pos.unrealized_profit)}
                        </p>
                        <p className={`text-[10px] font-mono ${pnl >= 0 ? 'text-profit' : 'text-loss'} opacity-70`}>
                          {pnlPct >= 0 ? '+' : ''}{formatPercent(pnlPct)}
                        </p>
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
