// client/src/components/portfolio/FuturesPortfolio.js
// =============================================================================
// 선물 포트폴리오 컴포넌트 - 백엔드 API 완벽 연동
// =============================================================================
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useFutures } from '../../contexts/FuturesContext';
import { useMarket } from '../../contexts/MarketContext';
import { formatPrice } from '../../utils/formatPrice';
import { toast } from 'react-toastify';

const FuturesPortfolio = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { 
    account, 
    accountLoading,
    positions, 
    positionsLoading,
    portfolio,
    portfolioLoading,
    transactions,
    fetchTransactions,
    closePosition,
    refreshAll 
  } = useFutures();
  const { realtimePrices } = useMarket();

  const [activeTab, setActiveTab] = useState('positions'); // positions, history, stats
  const [positionFilter, setPositionFilter] = useState('OPEN'); // OPEN, PENDING, CLOSED
  const [closingPositionId, setClosingPositionId] = useState(null);

  // 인증 체크
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  // 초기 데이터 로드
  useEffect(() => {
    if (isAuthenticated) {
      refreshAll();
      fetchTransactions(20, 0);
    }
  }, [isAuthenticated]);

  // ===========================================
  // 포지션 청산 핸들러
  // ===========================================
  const handleClosePosition = async (positionId) => {
    if (closingPositionId) return; // 이미 처리 중

    const confirmed = window.confirm('정말 이 포지션을 청산하시겠습니까?');
    if (!confirmed) return;

    setClosingPositionId(positionId);
    const result = await closePosition(positionId);
    setClosingPositionId(null);

    if (result.success) {
      // 데이터 새로고침은 closePosition 내부에서 처리됨
    }
  };

  // ===========================================
  // 로딩 상태
  // ===========================================
  if (accountLoading || portfolioLoading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-accent"></div>
      </div>
    );
  }

  // ===========================================
  // 렌더링
  // ===========================================
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">선물 포트폴리오</h1>
        <button
          onClick={refreshAll}
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
        >
          🔄 새로고침
        </button>
      </div>

      {/* 계정 요약 카드 */}
      <AccountSummary account={account} portfolio={portfolio} />

      {/* 탭 네비게이션 */}
      <div className="flex space-x-4 border-b border-gray-700">
        {[
          { id: 'positions', label: '포지션' },
          { id: 'history', label: '거래 내역' },
          { id: 'stats', label: '통계' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 -mb-px transition-colors ${
              activeTab === tab.id
                ? 'border-b-2 border-accent text-accent'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 탭 컨텐츠 */}
      {activeTab === 'positions' && (
        <PositionsTab
          positions={positions}
          positionsLoading={positionsLoading}
          realtimePrices={realtimePrices}
          filter={positionFilter}
          setFilter={setPositionFilter}
          onClose={handleClosePosition}
          closingId={closingPositionId}
        />
      )}

      {activeTab === 'history' && (
        <TransactionsTab transactions={transactions} />
      )}

      {activeTab === 'stats' && (
        <StatsTab portfolio={portfolio} />
      )}
    </div>
  );
};

// =============================================================================
// 계정 요약 컴포넌트
// =============================================================================
const AccountSummary = ({ account, portfolio }) => {
  if (!account) return null;

  const profitColor = (account.total_profit || 0) >= 0 ? 'text-green-400' : 'text-red-400';
  const unrealizedColor = (account.unrealized_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400';

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
      <SummaryCard
        label="총 자산"
        value={`$${formatPrice(account.total_balance || 0)}`}
        color="text-accent"
      />
      <SummaryCard
        label="사용 가능"
        value={`$${formatPrice(account.available_balance || account.balance || 0)}`}
      />
      <SummaryCard
        label="사용 중 증거금"
        value={`$${formatPrice(account.margin_used || 0)}`}
        color="text-yellow-400"
      />
      <SummaryCard
        label="미실현 손익"
        value={`$${formatPrice(account.unrealized_pnl || 0)}`}
        color={unrealizedColor}
        showSign
      />
      <SummaryCard
        label="실현 손익"
        value={`$${formatPrice(account.total_profit || 0)}`}
        color={profitColor}
        showSign
      />
      <SummaryCard
        label="증거금 비율"
        value={`${(account.margin_ratio || 0).toFixed(2)}%`}
        color={account.margin_ratio > 80 ? 'text-red-400' : 'text-white'}
      />
    </div>
  );
};

const SummaryCard = ({ label, value, color = 'text-white', showSign = false }) => (
  <div className="bg-gray-800 rounded-lg p-4">
    <p className="text-sm text-gray-400 mb-1">{label}</p>
    <p className={`text-xl font-bold ${color}`}>
      {showSign && parseFloat(value.replace(/[^0-9.-]/g, '')) > 0 && '+'}
      {value}
    </p>
  </div>
);

// =============================================================================
// 포지션 탭 컴포넌트
// =============================================================================
const PositionsTab = ({ 
  positions, 
  positionsLoading, 
  realtimePrices, 
  filter, 
  setFilter, 
  onClose, 
  closingId 
}) => {
  // 필터링된 포지션
  const filteredPositions = positions.filter(pos => pos.status === filter);

  return (
    <div className="space-y-4">
      {/* 필터 버튼 */}
      <div className="flex space-x-2">
        {['OPEN', 'PENDING', 'CLOSED'].map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`px-4 py-2 rounded-lg transition-colors ${
              filter === status
                ? 'bg-accent text-white'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
          >
            {status === 'OPEN' && '활성'}
            {status === 'PENDING' && '대기'}
            {status === 'CLOSED' && '종료'}
          </button>
        ))}
      </div>

      {/* 포지션 테이블 */}
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        {positionsLoading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
          </div>
        ) : filteredPositions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-gray-400 text-sm border-b border-gray-700">
                  <th className="text-left py-3 px-4">심볼</th>
                  <th className="text-left py-3 px-4">방향</th>
                  <th className="text-right py-3 px-4">수량</th>
                  <th className="text-right py-3 px-4">레버리지</th>
                  <th className="text-right py-3 px-4">진입가</th>
                  <th className="text-right py-3 px-4">현재가</th>
                  <th className="text-right py-3 px-4">청산가</th>
                  <th className="text-right py-3 px-4">미실현 손익</th>
                  <th className="text-right py-3 px-4">ROE</th>
                  {filter === 'OPEN' && <th className="text-center py-3 px-4">액션</th>}
                </tr>
              </thead>
              <tbody>
                {filteredPositions.map((pos) => {
                  const currentPrice = realtimePrices[pos.symbol] || pos.mark_price;
                  const pnlColor = pos.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400';
                  const sideColor = pos.side === 'LONG' ? 'text-green-400' : 'text-red-400';

                  return (
                    <tr key={pos.id} className="border-b border-gray-700 hover:bg-gray-750">
                      <td className="py-4 px-4 font-semibold">
                        {pos.symbol.replace('USDT', '')}
                      </td>
                      <td className={`py-4 px-4 font-semibold ${sideColor}`}>
                        {pos.side === 'LONG' ? '📈 롱' : '📉 숏'}
                      </td>
                      <td className="py-4 px-4 text-right">
                        {parseFloat(pos.quantity).toFixed(6)}
                      </td>
                      <td className="py-4 px-4 text-right text-yellow-400">
                        {pos.leverage}x
                      </td>
                      <td className="py-4 px-4 text-right">
                        ${formatPrice(pos.entry_price)}
                      </td>
                      <td className="py-4 px-4 text-right">
                        ${formatPrice(currentPrice)}
                      </td>
                      <td className="py-4 px-4 text-right text-orange-400">
                        ${formatPrice(pos.liquidation_price)}
                      </td>
                      <td className={`py-4 px-4 text-right font-semibold ${pnlColor}`}>
                        {pos.unrealized_pnl >= 0 ? '+' : ''}
                        ${formatPrice(pos.unrealized_pnl)}
                      </td>
                      <td className={`py-4 px-4 text-right font-bold ${pnlColor}`}>
                        {pos.roe_percent >= 0 ? '+' : ''}
                        {pos.roe_percent?.toFixed(2)}%
                      </td>
                      {filter === 'OPEN' && (
                        <td className="py-4 px-4 text-center">
                          <button
                            onClick={() => onClose(pos.id)}
                            disabled={closingId === pos.id}
                            className="px-3 py-1 bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-sm transition-colors"
                          >
                            {closingId === pos.id ? '처리중...' : '청산'}
                          </button>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-gray-400">
            <p className="text-lg mb-2">
              {filter === 'OPEN' && '활성 포지션이 없습니다'}
              {filter === 'PENDING' && '대기 중인 포지션이 없습니다'}
              {filter === 'CLOSED' && '종료된 포지션이 없습니다'}
            </p>
            {filter === 'OPEN' && (
              <button
                onClick={() => window.location.href = '/trade/BTCUSDT'}
                className="mt-4 px-6 py-2 bg-accent hover:bg-teal-600 rounded-lg transition-colors"
              >
                거래 시작하기
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// =============================================================================
// 거래 내역 탭 컴포넌트
// =============================================================================
const TransactionsTab = ({ transactions }) => {
  if (!transactions || transactions.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg p-8 text-center text-gray-400">
        <p>거래 내역이 없습니다</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-gray-400 text-sm border-b border-gray-700">
              <th className="text-left py-3 px-4">시간</th>
              <th className="text-left py-3 px-4">심볼</th>
              <th className="text-left py-3 px-4">타입</th>
              <th className="text-left py-3 px-4">방향</th>
              <th className="text-right py-3 px-4">수량</th>
              <th className="text-right py-3 px-4">가격</th>
              <th className="text-right py-3 px-4">레버리지</th>
              <th className="text-right py-3 px-4">손익</th>
              <th className="text-right py-3 px-4">수수료</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx) => {
              const pnlColor = tx.pnl >= 0 ? 'text-green-400' : 'text-red-400';
              const sideColor = tx.side === 'LONG' ? 'text-green-400' : 'text-red-400';
              const actionLabel = {
                OPEN: '🟢 진입',
                CLOSE: '🔴 청산',
                LIQUIDATION: '⚠️ 강청',
                LIMIT_FILLED: '📝 체결',
              };

              return (
                <tr key={tx.id} className="border-b border-gray-700 hover:bg-gray-750">
                  <td className="py-3 px-4 text-sm text-gray-400">
                    {new Date(tx.timestamp).toLocaleString('ko-KR')}
                  </td>
                  <td className="py-3 px-4 font-semibold">
                    {tx.symbol.replace('USDT', '')}
                  </td>
                  <td className="py-3 px-4">
                    {actionLabel[tx.action] || tx.action}
                  </td>
                  <td className={`py-3 px-4 ${sideColor}`}>
                    {tx.side}
                  </td>
                  <td className="py-3 px-4 text-right">
                    {parseFloat(tx.quantity).toFixed(6)}
                  </td>
                  <td className="py-3 px-4 text-right">
                    ${formatPrice(tx.price)}
                  </td>
                  <td className="py-3 px-4 text-right text-yellow-400">
                    {tx.leverage}x
                  </td>
                  <td className={`py-3 px-4 text-right font-semibold ${pnlColor}`}>
                    {tx.pnl !== 0 && (tx.pnl > 0 ? '+' : '')}
                    ${formatPrice(tx.pnl)}
                  </td>
                  <td className="py-3 px-4 text-right text-gray-400">
                    ${formatPrice(tx.fee)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// =============================================================================
// 통계 탭 컴포넌트
// =============================================================================
const StatsTab = ({ portfolio }) => {
  if (!portfolio) {
    return (
      <div className="bg-gray-800 rounded-lg p-8 text-center text-gray-400">
        <p>통계를 불러올 수 없습니다</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">거래 통계</h3>
        <div className="space-y-3">
          <StatRow label="총 거래 횟수" value={portfolio.total_trades || 0} />
          <StatRow 
            label="승률" 
            value={`${(portfolio.win_rate || 0).toFixed(1)}%`}
            color={portfolio.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}
          />
          <StatRow 
            label="평균 수익률" 
            value={`${(portfolio.avg_roe || 0).toFixed(2)}%`}
            color={portfolio.avg_roe >= 0 ? 'text-green-400' : 'text-red-400'}
          />
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">포지션 현황</h3>
        <div className="space-y-3">
          <StatRow label="활성 포지션" value={portfolio.open_positions_count || 0} color="text-green-400" />
          <StatRow label="대기 포지션" value={portfolio.pending_positions_count || 0} color="text-yellow-400" />
          <StatRow label="총 포지션 가치" value={`$${formatPrice(portfolio.total_position_value || 0)}`} />
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">자금 현황</h3>
        <div className="space-y-3">
          <StatRow label="총 자산" value={`$${formatPrice(portfolio.total_balance || 0)}`} color="text-accent" />
          <StatRow label="사용 가능" value={`$${formatPrice(portfolio.available_balance || 0)}`} />
          <StatRow 
            label="증거금 비율" 
            value={`${(portfolio.margin_ratio || 0).toFixed(2)}%`}
            color={portfolio.margin_ratio > 80 ? 'text-red-400' : 'text-white'}
          />
        </div>
      </div>
    </div>
  );
};

const StatRow = ({ label, value, color = 'text-white' }) => (
  <div className="flex justify-between">
    <span className="text-gray-400">{label}</span>
    <span className={`font-semibold ${color}`}>{value}</span>
  </div>
);

export default FuturesPortfolio;