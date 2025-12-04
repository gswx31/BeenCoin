// client/src/api/axios.js
// =============================================================================
// Axios 인스턴스 설정 - API 경로 수정
// =============================================================================
import axios from 'axios';

// ⭐ 핵심: baseURL에서 /api/v1 제거! (endpoints.js에서 이미 포함)
const instance = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// =============================================================================
// 요청 인터셉터: 모든 요청에 토큰 자동 추가
// =============================================================================
instance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // 디버깅용 로그
    if (process.env.NODE_ENV === 'development') {
      console.log(`📡 ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
    }
    
    return config;
  },
  (error) => Promise.reject(error)
);

// =============================================================================
// 응답 인터셉터: 에러 처리
// =============================================================================
instance.interceptors.response.use(
  (response) => response,
  (error) => {
    // 401 에러: 토큰 만료 또는 인증 실패
    if (error.response?.status === 401) {
      console.warn('🔒 인증 실패 - 토큰 정리');
      
      // 로그인/회원가입 페이지가 아닌 경우에만 처리
      const isAuthPage = window.location.pathname.includes('/login') || 
                        window.location.pathname.includes('/register');
      
      if (!isAuthPage) {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        
        // 리다이렉트는 AuthContext에서 처리하도록 함
        // window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

export default instance;