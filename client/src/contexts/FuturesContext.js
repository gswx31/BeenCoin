// client/src/contexts/FuturesContext.js
// =============================================================================
// 선물 거래 Context - 완전판
// =============================================================================
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from '../api/axios';
import { endpoints } from '../api/endpoints';
import { useAuth } from './AuthContext';
import { useMarket } from './MarketContext';
import { toast } from 'react-toastify';

const FuturesContext = createContext();

export const useFutures = () => {
  const context = useContext(FuturesContext);
  if (!context) {
    throw new Error('useFutures must be used within a FuturesProvider');
  }
  return context;
};

export const FuturesProvider = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const { realtimePrices } = useMarket();

  // 계정 상태
  const [account, setAccount] = useState(null);
  const [accountLoading, setAccountLoading] = useState(false);

  // 포지션 상태
  const [positions, setPositions] = useState([]);
  const [positionsLoading, setPositionsLoading] = useState(false);

  // 포트폴리오 상태
  const [portfolio, setPortfolio] = useState(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);

  // 거래 내역 상태
  const [transactions, setTransactions] = useState([]);
  const [transactionsLoading, setTransactionsLoading] = useState(false);

  // ===========================================
  // 계정 조회
  // ===========================================
  const fetchAccount = useCallback(async () => {
    if (!isAuthenticated) return;

    setAccountLoading(true);
    try {
      const response = await axios.get(endpoints.futures.account);
      setAccount(response.data);
    } catch (error) {
      console.error('❌ Failed to fetch futures account:', error);
    } finally {
      setAccountLoading(false);
    }
  }, [isAuthenticated]);

  // ===========================================
  // 포지션 조회
  // ===========================================
  const fetchPositions = useCallback(async () => {
    if (!isAuthenticated) return;

    setPositionsLoading(true);
    try {
      const response = await axios.get(endpoints.futures.positions);
      setPositions(response.data || []);
    } catch (error) {
      console.error('❌ Failed to fetch positions:', error);
      setPositions([]);
    } finally {
      setPositionsLoading(false);
    }
  }, [isAuthenticated]);

  // ===========================================
  // 포트폴리오 요약 조회
  // ===========================================
  const fetchPortfolioSummary = useCallback(async () => {
    if (!isAuthenticated) return;

    setPortfolioLoading(true);
    try {
      const response = await axios.get(endpoints.futures.portfolioSummary);
      setPortfolio(response.data);
    } catch (error) {
      console.error('❌ Failed to fetch portfolio summary:', error);
    } finally {
      setPortfolioLoading(false);
    }
  }, [isAuthenticated]);

  // ===========================================
  // 거래 내역 조회
  // ===========================================
  const fetchTransactions = useCallback(async (limit = 20, offset = 0) => {
    if (!isAuthenticated) return;

    setTransactionsLoading(true);
    try {
      const response = await axios.get(endpoints.futures.portfolioTransactions, {
        params: { limit, offset },
      });
      setTransactions(response.data || []);
    } catch (error) {
      console.error('❌ Failed to fetch transactions:', error);
      setTransactions([]);
    } finally {
      setTransactionsLoading(false);
    }
  }, [isAuthenticated]);

  // ===========================================
  // 초기 데이터 로드
  // ===========================================
  useEffect(() => {
    if (isAuthenticated) {
      fetchAccount();
      fetchPositions();
      fetchPortfolioSummary();
    }
  }, [isAuthenticated, fetchAccount, fetchPositions, fetchPortfolioSummary]);

  // ===========================================
  // 실시간 손익 업데이트
  // ===========================================
  useEffect(() => {
    if (!positions.length || !realtimePrices) return;

    setPositions((prevPositions) =>
      prevPositions.map((pos) => {
        if (pos.status !== 'OPEN') return pos;

        const currentPrice = realtimePrices[pos.symbol] || pos.mark_price;
        if (!currentPrice) return pos;

        const unrealizedPnl =
          pos.side === 'LONG'
            ? (currentPrice - pos.entry_price) * pos.quantity
            : (pos.entry_price - currentPrice) * pos.quantity;

        const roe = pos.margin ? (unrealizedPnl / pos.margin) * 100 : 0;

        return {
          ...pos,
          mark_price: currentPrice,
          unrealized_pnl: unrealizedPnl,
          roe_percent: roe,
        };
      })
    );
  }, [realtimePrices]);

  // ===========================================
  // 포지션 개설
  // ===========================================
  const openPosition = useCallback(async (orderData) => {
    try {
      console.log('📤 Opening position:', orderData);

      const response = await axios.post(endpoints.futures.openPosition, {
        symbol: orderData.symbol,
        side: orderData.side,
        quantity: orderData.quantity.toString(),
        leverage: orderData.leverage,
        order_type: orderData.orderType || 'MARKET',
        price: orderData.price?.toString(),
      });

      console.log('✅ Position opened:', response.data);

      const position = response.data;
      const priceDisplay = position.entry_price 
        ? `$${parseFloat(position.entry_price).toLocaleString()}`
        : 'PENDING';

      toast.success(
        `✅ ${position.side} ${position.symbol} 포지션 개설!\n` +
        `수량: ${position.quantity}\n` +
        `진입가: ${priceDisplay}\n` +
        `레버리지: ${position.leverage}x`,
        { autoClose: 5000 }
      );

      await Promise.all([fetchAccount(), fetchPositions()]);

      return { success: true, data: response.data };

    } catch (error) {
      console.error('❌ Failed to open position:', error);

      let errorMessage = '포지션 개설에 실패했습니다.';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }

      toast.error(errorMessage, { autoClose: 5000 });
      return { success: false, error: errorMessage };
    }
  }, [fetchAccount, fetchPositions]);

  // ===========================================
  // 포지션 청산
  // ===========================================
  const closePosition = useCallback(async (positionId) => {
    try {
      console.log('📤 Closing position:', positionId);

      const response = await axios.post(endpoints.futures.closePosition(positionId));

      console.log('✅ Position closed:', response.data);

      const result = response.data;
      const pnlColor = result.pnl >= 0 ? '🟢' : '🔴';
      const pnlSign = result.pnl >= 0 ? '+' : '';

      toast.success(
        `${pnlColor} ${result.symbol} 포지션 청산!\n` +
        `손익: ${pnlSign}$${parseFloat(result.pnl).toFixed(2)}\n` +
        `수익률: ${pnlSign}${parseFloat(result.roe_percent).toFixed(2)}%`,
        { autoClose: 5000 }
      );

      await Promise.all([fetchAccount(), fetchPositions()]);

      return { success: true, data: response.data };

    } catch (error) {
      console.error('❌ Failed to close position:', error);

      let errorMessage = '포지션 청산에 실패했습니다.';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }

      toast.error(errorMessage, { autoClose: 5000 });
      return { success: false, error: errorMessage };
    }
  }, [fetchAccount, fetchPositions]);

  // ===========================================
  // 대기 주문 취소
  // ===========================================
  const cancelPendingOrder = useCallback(async (positionId) => {
    try {
      console.log('📤 Cancelling pending order:', positionId);

      // 먼저 cancel 엔드포인트 시도, 없으면 close 사용
      let response;
      try {
        response = await axios.delete(endpoints.futures.cancelPosition(positionId));
      } catch (e) {
        // cancel 엔드포인트가 없으면 close 사용
        response = await axios.post(endpoints.futures.closePosition(positionId));
      }

      console.log('✅ Pending order cancelled:', response.data);

      toast.success('대기 주문이 취소되었습니다.', { autoClose: 3000 });

      await Promise.all([fetchAccount(), fetchPositions()]);

      return { success: true, data: response.data };

    } catch (error) {
      console.error('❌ Failed to cancel pending order:', error);

      let errorMessage = '주문 취소에 실패했습니다.';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }

      toast.error(errorMessage, { autoClose: 5000 });
      return { success: false, error: errorMessage };
    }
  }, [fetchAccount, fetchPositions]);

  // ===========================================
  // 체결 내역 조회
  // ===========================================
  const fetchPositionFills = useCallback(async (positionId) => {
    try {
      const response = await axios.get(endpoints.futures.positionFills(positionId));
      return response.data;
    } catch (error) {
      console.error('❌ Failed to fetch position fills:', error);
      return [];
    }
  }, []);

  // ===========================================
  // 통계 조회
  // ===========================================
  const fetchStats = useCallback(async () => {
    try {
      const response = await axios.get(endpoints.futures.portfolioStats);
      return response.data;
    } catch (error) {
      console.error('❌ Failed to fetch stats:', error);
      return null;
    }
  }, []);

  // ===========================================
  // 데이터 새로고침
  // ===========================================
  const refreshAll = useCallback(async () => {
    await Promise.all([
      fetchAccount(),
      fetchPositions(),
      fetchPortfolioSummary(),
    ]);
  }, [fetchAccount, fetchPositions, fetchPortfolioSummary]);

  // ===========================================
  // Context 값
  // ===========================================
  const value = {
    // 계정
    account,
    accountLoading,
    fetchAccount,

    // 포지션
    positions,
    positionsLoading,
    fetchPositions,

    // 포트폴리오
    portfolio,
    portfolioLoading,
    fetchPortfolioSummary,

    // 거래 내역
    transactions,
    transactionsLoading,
    fetchTransactions,

    // 액션
    openPosition,
    closePosition,
    cancelPendingOrder,
    fetchPositionFills,
    fetchStats,
    refreshAll,
  };

  return (
    <FuturesContext.Provider value={value}>
      {children}
    </FuturesContext.Provider>
  );
};

export default FuturesContext;