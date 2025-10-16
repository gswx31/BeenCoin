// client/src/api/axios.js - 개선 버전
import axios from 'axios';

// 환경변수에서 API URL 가져오기
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

console.log('🔗 API Base URL:', API_BASE_URL);

const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000, // 10초 타임아웃
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터: 토큰 자동 추가
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // 요청 로깅 (개발 환경)
    if (process.env.NODE_ENV === 'development') {
      console.log('📤 Request:', config.method?.toUpperCase(), config.url);
    }
    
    return config;
  },
  (error) => {
    console.error('❌ Request error:', error);
    return Promise.reject(error);
  }
);

// 응답 인터셉터: 에러 처리 및 로깅
axiosInstance.interceptors.response.use(
  (response) => {
    // 응답 로깅 (개발 환경)
    if (process.env.NODE_ENV === 'development') {
      console.log('📥 Response:', response.status, response.config.url);
    }
    return response;
  },
  (error) => {
    // 에러 로깅
    console.error('❌ Response error:', {
      status: error.response?.status,
      message: error.response?.data?.detail || error.message,
      url: error.config?.url
    });
    
    // 401 Unauthorized: 자동 로그아웃
    if (error.response?.status === 401) {
      console.warn('🔒 Unauthorized - redirecting to login');
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      
      // 현재 경로가 로그인 페이지가 아닐 때만 리다이렉트
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    
    // 403 Forbidden
    if (error.response?.status === 403) {
      console.warn('🚫 Forbidden - access denied');
    }
    
    // 503 Service Unavailable (Binance API 오류 등)
    if (error.response?.status === 503) {
      console.warn('⚠️ Service temporarily unavailable');
    }
    
    return Promise.reject(error);
  }
);

export default axiosInstance;


// ================================
// client/src/api/endpoints.js - API 엔드포인트 관리
// ================================
export const endpoints = {
  // 인증
  auth: {
    register: '/api/v1/auth/register',
    login: '/api/v1/auth/login',
  },
  
  // 계정
  account: {
    summary: '/api/v1/account/',
    transactions: '/api/v1/account/transactions',
  },
  
  // 주문
  orders: {
    create: '/api/v1/orders/',
    list: '/api/v1/orders/',
  },
  
  // 마켓
  market: {
    coins: '/api/v1/market/coins',
    coinDetail: (symbol) => `/api/v1/market/coin/${symbol}`,
    historical: (symbol) => `/api/v1/market/historical/${symbol}`,
    prices: '/api/v1/market/prices',
  },
  
  // WebSocket
  websocket: {
    realtime: (baseUrl) => `${baseUrl.replace('http', 'ws')}/ws/realtime`,
  }
};


// ================================
// client/src/api/services.js - API 서비스 함수들
// ================================
import axios from './axios';
import { endpoints } from './endpoints';

export const authService = {
  register: (username, password) => 
    axios.post(endpoints.auth.register, { username, password }),
  
  login: async (username, password) => {
    // OAuth2 형식으로 전송
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    return axios.post(endpoints.auth.login, formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
  },
};

export const accountService = {
  getSummary: () => axios.get(endpoints.account.summary),
  getTransactions: () => axios.get(endpoints.account.transactions),
};

export const orderService = {
  create: (orderData) => axios.post(endpoints.orders.create, orderData),
  list: () => axios.get(endpoints.orders.list),
};

export const marketService = {
  getCoins: () => axios.get(endpoints.market.coins),
  getCoinDetail: (symbol) => axios.get(endpoints.market.coinDetail(symbol)),
  getHistorical: (symbol, interval = '1h', limit = 24) => 
    axios.get(endpoints.market.historical(symbol), {
      params: { interval, limit }
    }),
  getPrices: () => axios.get(endpoints.market.prices),
};