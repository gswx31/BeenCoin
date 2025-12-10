// client/src/api/endpoints.js
// =============================================================================
// API 엔드포인트 정의 - 호가창/체결내역 추가
// =============================================================================

const API_V1 = '/api/v1';

export const endpoints = {
  // 인증
  auth: {
    login: `${API_V1}/auth/login`,
    register: `${API_V1}/auth/register`,
    me: `${API_V1}/auth/me`,
    refresh: `${API_V1}/auth/refresh`,
    checkUsername: (username) => `${API_V1}/auth/check-username/${username}`,
  },

  // 마켓 데이터
  market: {
    coins: `${API_V1}/market/coins`,
    coin: (symbol) => `${API_V1}/market/coin/${symbol}`,
    klines: `${API_V1}/market/klines`,
    historical: (symbol) => `${API_V1}/market/historical/${symbol}`,
    
    // ⭐ 추가: 호가창 & 체결내역
    orderbook: `${API_V1}/market/orderbook`,  // GET /orderbook/{symbol}
    trades: `${API_V1}/market/trades`,        // GET /trades/{symbol}
  },

  // 현물 주문
  orders: {
    list: `${API_V1}/orders`,
    create: `${API_V1}/orders`,
    cancel: (orderId) => `${API_V1}/orders/${orderId}`,
    detail: (orderId) => `${API_V1}/orders/${orderId}`,
  },

  // 계정
  account: {
    summary: `${API_V1}/account`,
    balance: `${API_V1}/account/balance`,
    positions: `${API_V1}/account/positions`,
    transactions: `${API_V1}/account/transactions`,
  },

  // 선물 거래
  futures: {
    account: `${API_V1}/futures/account`,
    positions: `${API_V1}/futures/positions`,
    openPosition: `${API_V1}/futures/positions/open`,
    closePosition: (positionId) => `${API_V1}/futures/positions/${positionId}/close`,
    orders: `${API_V1}/futures/orders`,
    transactions: `${API_V1}/futures/transactions`,
    portfolioSummary: `${API_V1}/futures/portfolio/summary`,
  },

  // ⭐ 추가: 손절/익절 주문
  stopOrders: {
    list: `${API_V1}/stop-orders`,
    create: `${API_V1}/stop-orders`,
    oco: `${API_V1}/stop-orders/oco`,
    detail: (orderId) => `${API_V1}/stop-orders/${orderId}`,
    cancel: (orderId) => `${API_V1}/stop-orders/${orderId}`,
    alerts: `${API_V1}/stop-orders/alerts`,
  },

  // WebSocket
  websocket: {
    realtime: '/ws/realtime',
    prices: (symbol) => `/ws/prices/${symbol}`,
    orderbook: (symbol) => `/ws/orderbook/${symbol}`,
    trades: (symbol) => `/ws/trades/${symbol}`,
  },
};

// WebSocket URL 생성 헬퍼
export const getWebSocketUrl = (path) => {
  const wsBase = process.env.REACT_APP_WS_URL || 
    (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + 
    window.location.host;
  return `${wsBase}${path}`;
};

export default endpoints;