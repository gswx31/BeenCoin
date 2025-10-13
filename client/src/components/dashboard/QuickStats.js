// client/src/components/dashboard/QuickStats.js
import React, { useState, useEffect } from 'react';
import axios from '../../api/axios';

const QuickStats = () => {
  const [account, setAccount] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAccountData();
  }, []);

  const fetchAccountData = async () => {
    try {
      const response = await axios.get('/api/v1/account/');
      setAccount(response.data);
    } catch (error) {
      console.error('Failed to fetch account data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex space-x-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-gray-800 rounded-lg p-4 w-32 h-20 animate-pulse"></div>
        ))}
      </div>
    );
  }

  if (!account) return null;

  const profitColor = parseFloat(account.profit_rate) >= 0 ? 'text-green-400' : 'text-red-400';

  return (
    <div className="flex space-x-4">
      <div className="bg-gray-800 rounded-lg p-4 min-w-[150px]">
        <div className="text-sm text-gray-400">총 자산</div>
        <div className="text-xl font-bold">
          ${parseFloat(account.total_value).toLocaleString('ko-KR', { maximumFractionDigits: 2 })}
        </div>
      </div>
      <div className="bg-gray-800 rounded-lg p-4 min-w-[150px]">
        <div className="text-sm text-gray-400">수익률</div>
        <div className={`text-xl font-bold ${profitColor}`}>
          {parseFloat(account.profit_rate) >= 0 ? '+' : ''}
          {parseFloat(account.profit_rate).toFixed(2)}%
        </div>
      </div>
      <div className="bg-gray-800 rounded-lg p-4 min-w-[150px]">
        <div className="text-sm text-gray-400">보유 현금</div>
        <div className="text-xl font-bold">
          ${parseFloat(account.balance).toLocaleString('ko-KR', { maximumFractionDigits: 2 })}
        </div>
      </div>
    </div>
  );
};

export default QuickStats;