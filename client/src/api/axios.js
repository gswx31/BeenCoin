// client/src/api/axios.js
// =============================================================================
// Axios 인스턴스 - 보안 강화 및 에러 처리 개선
// =============================================================================
import axios from 'axios';
import { toast } from 'react-toastify';

// 환경변수에서 API URL 가져오기
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

console.log('🔗 API Base URL:', API_BASE_URL);

// Axios 인스턴스 생성
const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000, // 15초 타임아웃
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false, // CORS 설정에 따라 조정
});

// =============================================================================
// 요청 인터셉터
// =============================================================================
axiosInstance.interceptors.request.use(
  (config) => {
    // 토큰 자동 추가
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // 요청 ID 추가 (디버깅용)
    config.headers['X-Request-ID'] = generateRequestId();

    // 개발 환경 로깅
    if (process.env.NODE_ENV === 'development') {
      console.log(
        `📤 ${config.method?.toUpperCase()} ${config.url}`,
        config.data ? '| Data:' : '',
        config.data || ''
      );
    }

    return config;
  },
  (error) => {
    console.error('❌ Request setup error:', error);
    return Promise.reject(error);
  }
);

// =============================================================================
// 응답 인터셉터
// =============================================================================
axiosInstance.interceptors.response.use(
  (response) => {
    // 개발 환경 로깅
    if (process.env.NODE_ENV === 'development') {
      console.log(
        `📥 ${response.status} ${response.config.url}`,
        response.data ? '| Data available' : ''
      );
    }

    // Rate Limit 헤더 확인
    const remaining = response.headers['x-ratelimit-remaining'];
    if (remaining && parseInt(remaining) < 10) {
      console.warn(`⚠️ Rate limit warning: ${remaining} requests remaining`);
    }

    return response;
  },
  (error) => {
    // 에러 상세 정보 추출
    const status = error.response?.status;
    const detail = error.response?.data?.detail;
    const requestId = error.response?.headers?.['x-request-id'];

    // 에러 로깅
    console.error('❌ API Error:', {
      status,
      message: detail || error.message,
      url: error.config?.url,
      requestId,
    });

    // 상태 코드별 처리
    switch (status) {
      case 401:
        // 인증 실패 - 로그아웃 처리
        handleUnauthorized();
        break;

      case 403:
        // 권한 없음
        toast.error('접근 권한이 없습니다.');
        break;

      case 404:
        // 리소스 없음
        console.warn('Resource not found:', error.config?.url);
        break;

      case 422:
        // 유효성 검증 실패
        handleValidationError(error.response?.data);
        break;

      case 429:
        // Rate Limit 초과
        handleRateLimitError(error.response);
        break;

      case 500:
      case 502:
      case 503:
        // 서버 에러
        toast.error('서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        break;

      default:
        // 네트워크 에러 등
        if (!error.response) {
          toast.error('서버에 연결할 수 없습니다. 네트워크를 확인해주세요.');
        }
    }

    return Promise.reject(error);
  }
);

// =============================================================================
// 헬퍼 함수
// =============================================================================

/**
 * 랜덤 요청 ID 생성
 */
function generateRequestId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * 401 Unauthorized 처리
 */
function handleUnauthorized() {
  const currentPath = window.location.pathname;

  // 이미 로그인 페이지인 경우 무시
  if (currentPath === '/login' || currentPath === '/register') {
    return;
  }

  console.warn('🔒 Session expired - clearing auth data');

  // 토큰 제거
  localStorage.removeItem('token');
  localStorage.removeItem('username');

  // 로그인 페이지로 리다이렉트
  toast.warning('세션이 만료되었습니다. 다시 로그인해주세요.');

  // 약간의 지연 후 리다이렉트 (토스트 표시를 위해)
  setTimeout(() => {
    window.location.href = '/login';
  }, 1000);
}

/**
 * 유효성 검증 에러 처리
 */
function handleValidationError(data) {
  if (data?.detail) {
    // FastAPI 유효성 검증 에러 형식
    if (Array.isArray(data.detail)) {
      data.detail.forEach((err) => {
        const field = err.loc?.join('.') || 'field';
        const msg = err.msg || 'Invalid value';
        toast.error(`${field}: ${msg}`);
      });
    } else if (typeof data.detail === 'string') {
      toast.error(data.detail);
    } else if (typeof data.detail === 'object') {
      toast.error(data.detail.message || '입력값을 확인해주세요.');
    }
  }
}

/**
 * Rate Limit 에러 처리
 */
function handleRateLimitError(response) {
  const retryAfter = response?.headers?.['retry-after'];
  const message = response?.data?.detail?.message || '요청이 너무 많습니다.';

  if (retryAfter) {
    toast.error(`${message} ${retryAfter}초 후 다시 시도해주세요.`);
  } else {
    toast.error(`${message} 잠시 후 다시 시도해주세요.`);
  }
}

// =============================================================================
// API 서비스 함수
// =============================================================================

export const apiService = {
  // GET 요청
  get: (url, config = {}) => axiosInstance.get(url, config),

  // POST 요청
  post: (url, data, config = {}) => axiosInstance.post(url, data, config),

  // PUT 요청
  put: (url, data, config = {}) => axiosInstance.put(url, data, config),

  // DELETE 요청
  delete: (url, config = {}) => axiosInstance.delete(url, config),

  // FormData POST (로그인 등)
  postForm: (url, data, config = {}) => {
    const formData = new URLSearchParams();
    Object.entries(data).forEach(([key, value]) => {
      formData.append(key, value);
    });

    return axiosInstance.post(url, formData, {
      ...config,
      headers: {
        ...config.headers,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
  },
};

export default axiosInstance;