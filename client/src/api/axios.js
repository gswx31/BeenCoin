// client/src/api/axios.js
// =============================================================================
// Axios 인스턴스 설정 - 토큰 자동 관리 및 인터셉터
// =============================================================================
import axios from 'axios';

// Axios 인스턴스 생성
const instance = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1',
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
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// =============================================================================
// 응답 인터셉터: 401 오류 시 자동 로그아웃
// =============================================================================
instance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 토큰 만료 또는 인증 실패
      console.warn('🔒 Unauthorized - clearing auth data');
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      
      // 로그인 페이지로 리다이렉트 (현재 페이지가 로그인/회원가입이 아닌 경우)
      const isAuthPage = window.location.pathname.includes('/login') || 
                        window.location.pathname.includes('/register');
      
      if (!isAuthPage) {
        console.log('🔄 Redirecting to login...');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// =============================================================================
// FormData 전송을 위한 헬퍼
// =============================================================================
export const apiService = {
  postForm: async (url, data) => {
    const formData = new URLSearchParams();
    Object.keys(data).forEach(key => {
      formData.append(key, data[key]);
    });
    
    return instance.post(url, formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
  },
};

export default instance;