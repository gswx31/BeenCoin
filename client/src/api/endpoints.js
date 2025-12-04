// client/src/api/endpoints.js
// =============================================================================
// API 엔드포인트 중앙 관리 - 선물 거래 전용
// =============================================================================

const API_V1 = '/api/v1';

export const endpoints = {
  // =========================================
  // 인증 (Auth)
  // =========================================
  auth: {
    register: `${API_V1}/auth/register`,
    login: `${API_V1}/auth/login`,
    me: `${API_V1}/auth/me`,
    checkUsername: (username) => `${API_V1}/auth/check-username/${username}`,  // ⭐ NEW
    changePassword: `${API_V1}/auth/change-password`,
    checkPasswordStrength: `${API_V1}/auth/check-password-strength`,
  },

  // =========================================
  // 선물 거래 (Futures)
  // =========================================
  futures: {
    // 계정
    account: `${API_V1}/futures/account`,
    
    // 포지션
    openPosition: `${API_V1}/futures/positions/open`,
    closePosition: (positionId) => `${API_V1}/futures/positions/${positionId}/close`,
    cancelPosition: (positionId) => `${API_V1}/futures/positions/${positionId}/cancel`,
    positions: `${API_V1}/futures/positions`,
    
    // 포트폴리오
    portfolioSummary: `${API_V1}/futures/portfolio/summary`,
    portfolioPositions: `${API_V1}/futures/portfolio/positions`,
    portfolioTransactions: `${API_V1}/futures/portfolio/transactions`,
    portfolioStats: `${API_V1}/futures/portfolio/stats`,
    positionFills: (positionId) => `${API_V1}/futures/portfolio/fills/${positionId}`,
  },

  // =========================================
  // 마켓 데이터 (Market)
  // =========================================
  market: {
    coins: `${API_V1}/market/coins`,
    coinDetail: (symbol) => `${API_V1}/market/coin/${symbol}`,
    historical: (symbol) => `${API_V1}/market/historical/${symbol}`,
    prices: `${API_V1}/market/prices`,
    trades: (symbol) => `${API_V1}/market/trades/${symbol}`,
    orderbook: (symbol) => `${API_V1}/market/orderbook/${symbol}`,
  },

  // =========================================
  // 알림 (Alerts)
  // =========================================
  alerts: {
    create: `${API_V1}/alerts/`,
    list: `${API_V1}/alerts/`,
    delete: (alertId) => `${API_V1}/alerts/${alertId}`,
  },

  // =========================================
  // WebSocket
  // =========================================
  websocket: {
    realtime: '/ws/realtime',
    prices: (symbol) => `/ws/prices/${symbol}`,
  },
};

// 헬퍼 함수: WebSocket URL 생성
export const getWebSocketUrl = (path) => {
  const baseUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
  return `${baseUrl}${path}`;
};

export default endpoints;