// client/src/contexts/FuturesContext.js
// =============================================================================
// 선물 거래 Context - 포지션, 계정, 주문 관리
// =============================================================================
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from '../api/axios';
import { endpoints } from '../api/endpoints';
import { useAuth } from './AuthContext';
import { useMarket } from './MarketContext';
import { toast } from 'react-toastify';

const FuturesContext = createContext(null);

export const useFutures = () => {
  const context = useContext(FuturesContext);
  if (!context) {
    throw new Error('useFutures must be used within a FuturesProvider');
  }
  return context;
};

// =============================================================================
// FuturesProvider 컴포넌트
// =============================================================================
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

  // 거래 내역
  const [transactions, setTransactions] = useState([]);
  const [transactionsLoading, setTransactionsLoading] = useState(false);

  // ===========================================
  // 인증 상태 변경 시 데이터 로드
  // ===========================================
  useEffect(() => {
    if (isAuthenticated) {
      fetchAccount();
      fetchPositions();
      fetchPortfolioSummary();
    } else {
      // 로그아웃 시 초기화
      setAccount(null);
      setPositions([]);
      setPortfolio(null);
      setTransactions([]);
    }
  }, [isAuthenticated]);

  // 실시간 가격 변경 시 포지션 PnL 업데이트
  useEffect(() => {
    if (positions.length > 0 && Object.keys(realtimePrices).length > 0) {
      updatePositionsPnL();
    }
  }, [realtimePrices, positions.length]);

  // ===========================================
  // 계정 정보 조회
  // ===========================================
  const fetchAccount = useCallback(async () => {
    if (!isAuthenticated) return;

    setAccountLoading(true);
    try {
      const response = await axios.get(endpoints.futures.account);
      setAccount(response.data);
      console.log('📊 Futures account loaded:', response.data);
    } catch (error) {
      console.error('❌ Failed to fetch futures account:', error);
      // 404면 계정이 아직 생성되지 않음 (정상)
      if (error.response?.status !== 404) {
        toast.error('계정 정보를 불러올 수 없습니다.');
      }
    } finally {
      setAccountLoading(false);
    }
  }, [isAuthenticated]);

  // ===========================================
  // 포지션 목록 조회
  // ===========================================
  const fetchPositions = useCallback(async (status = 'OPEN') => {
    if (!isAuthenticated) return;

    setPositionsLoading(true);
    try {
      const response = await axios.get(endpoints.futures.positions, {
        params: { status },
      });
      setPositions(response.data);
      console.log(`📊 Futures positions (${status}):`, response.data.length);
    } catch (error) {
      console.error('❌ Failed to fetch positions:', error);
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
      console.log('📊 Portfolio summary loaded:', response.data);
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
      setTransactions(response.data);
      console.log('📊 Transactions loaded:', response.data.length);
      return response.data;
    } catch (error) {
      console.error('❌ Failed to fetch transactions:', error);
      return [];
    } finally {
      setTransactionsLoading(false);
    }
  }, [isAuthenticated]);

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

      // 성공 알림
      const position = response.data;
      toast.success(
        `✅ ${position.side} ${position.symbol} 포지션 개설!\n` +
        `수량: ${position.quantity}\n` +
        `진입가: $${position.entry_price.toLocaleString()}\n` +
        `레버리지: ${position.leverage}x`,
        { autoClose: 5000 }
      );

      // 데이터 새로고침
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

      // 성공 알림
      const result = response.data;
      const pnlColor = result.pnl >= 0 ? '🟢' : '🔴';
      const pnlSign = result.pnl >= 0 ? '+' : '';

      toast.success(
        `${pnlColor} ${result.symbol} 포지션 청산!\n` +
        `손익: ${pnlSign}$${result.pnl.toFixed(2)}\n` +
        `수익률: ${pnlSign}${result.roe_percent.toFixed(2)}%`,
        { autoClose: 5000 }
      );

      // 데이터 새로고침
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
  // 포지션 PnL 실시간 업데이트
  // ===========================================
  const updatePositionsPnL = useCallback(() => {
    setPositions((prevPositions) =>
      prevPositions.map((pos) => {
        const currentPrice = realtimePrices[pos.symbol];
        if (!currentPrice) return pos;

        // PnL 계산
        let unrealizedPnl;
        if (pos.side === 'LONG') {
          unrealizedPnl = (currentPrice - pos.entry_price) * pos.quantity;
        } else {
          unrealizedPnl = (pos.entry_price - currentPrice) * pos.quantity;
        }

        // ROE 계산
        const roe = pos.margin > 0 ? (unrealizedPnl / pos.margin) * 100 : 0;

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