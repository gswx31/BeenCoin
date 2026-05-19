import React, { useEffect, useState } from 'react';
import api from '../api';

const TierBadge = ({ compact = false }) => {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get('/tier/me').then(({ data }) => setData(data)).catch(() => {});
  }, []);

  if (!data) return null;
  const { tier, next_tier, progress, return_pct, trade_count } = data;

  if (compact) {
    return (
      <span className="inline-flex items-center space-x-1 px-2 py-1 rounded-full bg-dark-700 border border-dark-600">
        <span>{tier.emoji}</span>
        <span className="text-[10px] font-bold" style={{ color: tier.color }}>{tier.label}</span>
      </span>
    );
  }

  return (
    <div className="bg-dark-800 rounded-2xl border border-dark-600 p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <span className="text-3xl">{tier.emoji}</span>
          <div>
            <p className="text-[10px] text-muted">현재 티어</p>
            <p className="text-lg font-bold" style={{ color: tier.color }}>{tier.label}</p>
          </div>
        </div>
        {tier.fee_discount > 0 && (
          <span className="text-[10px] text-mint">수수료 -{tier.fee_discount}%</span>
        )}
      </div>

      {next_tier ? (
        <>
          <div className="flex items-center justify-between text-[10px] mb-1.5">
            <span className="text-muted">다음: {next_tier.emoji} {next_tier.label}</span>
            <span className="text-accent">{progress}%</span>
          </div>
          <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-accent to-mint rounded-full transition-all"
              style={{ width: `${progress}%` }} />
          </div>
          <p className="text-[10px] text-dark-400 mt-1.5">
            수익률 {return_pct}% · 거래 {trade_count}회 · 다음 티어: 수익률 {next_tier.min_return}%+ · 거래 {next_tier.min_trades}회+
          </p>
        </>
      ) : (
        <p className="text-[10px] text-accent text-center">최고 티어 달성! 👑</p>
      )}
    </div>
  );
};

export default TierBadge;
