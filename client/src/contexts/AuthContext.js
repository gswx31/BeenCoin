// client/src/contexts/AuthContext.js
// =============================================================================
// 인증 Context - 보안 강화 버전
// =============================================================================
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios, { apiService } from '../api/axios';
import { endpoints } from '../api/endpoints';
import { toast } from 'react-toastify';

const AuthContext = createContext(null);

// Context Hook
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// =============================================================================
// AuthProvider 컴포넌트
// =============================================================================
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [tokenExpiry, setTokenExpiry] = useState(null);

  // ===========================================
  // 초기 인증 상태 확인
  // ===========================================
  useEffect(() => {
    checkAuth();
  }, []);

  // 토큰 만료 체크 (자동 로그아웃)
  useEffect(() => {
    if (!tokenExpiry) return;

    const checkExpiry = () => {
      if (Date.now() >= tokenExpiry) {
        console.warn('🔒 Token expired');
        logout();
        toast.warning('세션이 만료되었습니다. 다시 로그인해주세요.');
      }
    };

    // 1분마다 체크
    const interval = setInterval(checkExpiry, 60000);
    return () => clearInterval(interval);
  }, [tokenExpiry]);

  // ===========================================
  // 인증 상태 확인
  // ===========================================
  const checkAuth = useCallback(async () => {
    const token = localStorage.getItem('token');

    if (!token) {
      setLoading(false);
      return;
    }

    try {
      // 토큰 유효성 검증 (백엔드 /auth/me 호출)
      const response = await axios.get(endpoints.auth.me);
      
      setUser(response.data);
      setIsAuthenticated(true);

      // 토큰 만료 시간 설정 (백엔드에서 받은 경우)
      if (response.data.token_expiry) {
        setTokenExpiry(new Date(response.data.token_expiry).getTime());
      }

    } catch (error) {
      console.error('Auth check failed:', error);
      
      // 토큰이 유효하지 않으면 제거
      clearAuthData();
    } finally {
      setLoading(false);
    }
  }, []);

  // ===========================================
  // 로그인
  // ===========================================
  const login = useCallback(async (username, password) => {
    try {
      // 입력값 검증
      if (!username?.trim()) {
        toast.error('아이디를 입력해주세요.');
        return false;
      }
      if (!password) {
        toast.error('비밀번호를 입력해주세요.');
        return false;
      }

      console.log('🔐 Login attempt:', username);

      // FormData 형식으로 로그인 요청
      const response = await apiService.postForm(endpoints.auth.login, {
        username: username.trim(),
        password: password,
      });

      console.log('✅ Login successful');

      const { access_token, expires_in } = response.data;

      // 토큰 저장
      localStorage.setItem('token', access_token);
      localStorage.setItem('username', username);

      // 사용자 정보 설정
      setUser({ username });
      setIsAuthenticated(true);

      // 토큰 만료 시간 설정
      if (expires_in) {
        setTokenExpiry(Date.now() + expires_in * 1000);
      }

      toast.success(`환영합니다, ${username}님! 🎉`);
      return true;

    } catch (error) {
      console.error('❌ Login error:', error);

      // 에러 메시지 처리
      let errorMessage = '로그인에 실패했습니다.';

      if (!error.response) {
        errorMessage = '서버에 연결할 수 없습니다.';
      } else if (error.response.status === 401) {
        errorMessage = '아이디 또는 비밀번호가 올바르지 않습니다.';
      } else if (error.response.status === 429) {
        const retryAfter = error.response.data?.detail?.retry_after || 60;
        errorMessage = `로그인 시도가 너무 많습니다. ${retryAfter}초 후 다시 시도해주세요.`;
        
        // 로그인 차단 경고
        if (error.response.data?.detail?.warning) {
          toast.warning(error.response.data.detail.warning);
        }
      } else if (error.response.data?.detail) {
        if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
        } else if (error.response.data.detail.message) {
          errorMessage = error.response.data.detail.message;
        }
      }

      toast.error(errorMessage, { autoClose: 5000 });
      return false;
    }
  }, []);

  // ===========================================
  // 회원가입
  // ===========================================
  const register = useCallback(async (username, password) => {
    try {
      // 클라이언트 사이드 검증
      if (!validateUsername(username)) {
        return false;
      }
      if (!validatePassword(password)) {
        return false;
      }

      console.log('📝 Register attempt:', username);

      const response = await axios.post(endpoints.auth.register, {
        username,
        password,
      });

      console.log('✅ Register successful:', response.data);
      toast.success('회원가입 성공! 로그인해주세요. 🎉');
      return true;

    } catch (error) {
      console.error('❌ Register error:', error);

      let errorMessage = '회원가입에 실패했습니다.';

      if (error.response?.status === 400) {
        errorMessage = error.response.data?.detail || '이미 존재하는 사용자명입니다.';
      } else if (error.response?.status === 422) {
        // 유효성 검증 에러
        const details = error.response.data?.detail;
        if (Array.isArray(details)) {
          errorMessage = details.map(d => d.msg).join('\n');
        } else if (typeof details === 'string') {
          errorMessage = details;
        }
      } else if (error.response?.status === 429) {
        errorMessage = '회원가입 시도가 너무 많습니다. 잠시 후 다시 시도해주세요.';
      }

      toast.error(errorMessage, { autoClose: 5000 });
      return false;
    }
  }, []);

  // ===========================================
  // 로그아웃
  // ===========================================
  const logout = useCallback(() => {
    console.log('👋 Logging out');
    clearAuthData();
    toast.info('로그아웃되었습니다.');
  }, []);

  // ===========================================
  // 비밀번호 변경
  // ===========================================
  const changePassword = useCallback(async (currentPassword, newPassword, confirmPassword) => {
    try {
      if (newPassword !== confirmPassword) {
        toast.error('새 비밀번호가 일치하지 않습니다.');
        return false;
      }

      await axios.post(endpoints.auth.changePassword, {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });

      toast.success('비밀번호가 변경되었습니다.');
      return true;

    } catch (error) {
      const errorMessage = error.response?.data?.detail || '비밀번호 변경에 실패했습니다.';
      toast.error(errorMessage);
      return false;
    }
  }, []);

  // ===========================================
  // 헬퍼 함수
  // ===========================================
  const clearAuthData = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    setUser(null);
    setIsAuthenticated(false);
    setTokenExpiry(null);
  };

  const validateUsername = (username) => {
    if (!username || username.length < 3) {
      toast.error('아이디는 3자 이상이어야 합니다.');
      return false;
    }
    if (username.length > 20) {
      toast.error('아이디는 20자 이하여야 합니다.');
      return false;
    }
    if (!/^[a-zA-Z0-9]+$/.test(username)) {
      toast.error('아이디는 영문자와 숫자만 사용 가능합니다.');
      return false;
    }
    return true;
  };

  const validatePassword = (password) => {
    if (!password || password.length < 8) {
      toast.error('비밀번호는 8자 이상이어야 합니다.');
      return false;
    }
    if (password.length > 128) {
      toast.error('비밀번호는 128자 이하여야 합니다.');
      return false;
    }
    // 복잡도 검증 (보안 강화)
    if (!/[A-Z]/.test(password)) {
      toast.error('비밀번호에 대문자가 포함되어야 합니다.');
      return false;
    }
    if (!/[a-z]/.test(password)) {
      toast.error('비밀번호에 소문자가 포함되어야 합니다.');
      return false;
    }
    if (!/\d/.test(password)) {
      toast.error('비밀번호에 숫자가 포함되어야 합니다.');
      return false;
    }
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      toast.error('비밀번호에 특수문자가 포함되어야 합니다.');
      return false;
    }
    return true;
  };

  // ===========================================
  // Context 값
  // ===========================================
  const value = {
    user,
    isAuthenticated,
    loading,
    login,
    register,
    logout,
    changePassword,
    checkAuth,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;