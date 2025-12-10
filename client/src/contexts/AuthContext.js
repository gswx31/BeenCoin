// client/src/contexts/AuthContext.js
// =============================================================================
// 인증 Context - 새로고침 깜빡임 완전 해결 버전
// =============================================================================
import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import axios from '../api/axios';
import { endpoints } from '../api/endpoints';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  // ⭐ 핵심 개선: 초기 상태를 localStorage에서 즉시 복원
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('user');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return !!localStorage.getItem('token');
  });
  
  // ⭐ 초기 로딩은 토큰이 있을 때만 true (검증 필요)
  const [loading, setLoading] = useState(() => {
    return !!localStorage.getItem('token');
  });
  
  // 토큰 검증 중복 방지
  const isValidating = useRef(false);
  
  // 토큰 만료 타이머
  const tokenRefreshTimer = useRef(null);

  // ===========================================
  // ⭐ 토큰 디코딩 (만료 시간 확인용)
  // ===========================================
  const decodeToken = useCallback((token) => {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload);
    } catch (e) {
      return null;
    }
  }, []);

  // ===========================================
  // ⭐ 토큰 만료 체크
  // ===========================================
  const isTokenExpired = useCallback((token) => {
    const payload = decodeToken(token);
    if (!payload || !payload.exp) return true;
    
    // 30초 여유를 두고 만료 체크
    return payload.exp * 1000 < Date.now() + 30000;
  }, [decodeToken]);

  // ===========================================
  // 인증 정보 초기화
  // ===========================================
  const clearAuth = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('user');
    setUser(null);
    setIsAuthenticated(false);
    
    if (tokenRefreshTimer.current) {
      clearTimeout(tokenRefreshTimer.current);
      tokenRefreshTimer.current = null;
    }
  }, []);

  // ===========================================
  // ⭐ 토큰 갱신 스케줄링
  // ===========================================
  const scheduleTokenRefresh = useCallback((token) => {
    const payload = decodeToken(token);
    if (!payload || !payload.exp) return;
    
    // 만료 5분 전에 갱신 시도
    const expiresIn = payload.exp * 1000 - Date.now();
    const refreshTime = Math.max(expiresIn - 5 * 60 * 1000, 60000); // 최소 1분
    
    if (tokenRefreshTimer.current) {
      clearTimeout(tokenRefreshTimer.current);
    }
    
    tokenRefreshTimer.current = setTimeout(async () => {
      console.log('🔄 토큰 자동 갱신 시도...');
      try {
        const response = await axios.post(endpoints.auth.refresh);
        const { access_token } = response.data;
        
        localStorage.setItem('token', access_token);
        scheduleTokenRefresh(access_token);
        console.log('✅ 토큰 갱신 성공');
      } catch (error) {
        console.warn('⚠️ 토큰 갱신 실패, 재로그인 필요');
        // 갱신 실패해도 즉시 로그아웃하지 않음 (기존 토큰이 아직 유효할 수 있음)
      }
    }, refreshTime);
    
    console.log(`⏰ 토큰 갱신 예약: ${Math.round(refreshTime / 60000)}분 후`);
  }, [decodeToken]);

  // ===========================================
  // 사용자 정보 조회 (백그라운드 검증)
  // ===========================================
  const fetchUser = useCallback(async (silent = false) => {
    if (isValidating.current) return null;
    isValidating.current = true;
    
    try {
      const response = await axios.get(endpoints.auth.me);
      
      const userData = response.data;
      setUser(userData);
      setIsAuthenticated(true);
      
      // ⭐ 사용자 정보도 localStorage에 저장 (새로고침 시 즉시 복원용)
      localStorage.setItem('user', JSON.stringify(userData));
      
      if (response.data.username) {
        localStorage.setItem('username', response.data.username);
      }
      
      // 토큰 갱신 스케줄링
      const token = localStorage.getItem('token');
      if (token) {
        scheduleTokenRefresh(token);
      }
      
      if (!silent) {
        console.log('✅ 사용자 정보 확인:', userData.username);
      }
      
      return userData;
    } catch (error) {
      if (!silent) {
        console.error('❌ 사용자 정보 조회 실패:', error);
      }
      
      if (error.response?.status === 401 || error.response?.status === 403) {
        clearAuth();
      }
      
      throw error;
    } finally {
      isValidating.current = false;
    }
  }, [clearAuth, scheduleTokenRefresh]);

  // ===========================================
  // ⭐ 앱 시작 시 토큰 검증 (백그라운드)
  // ===========================================
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('token');
      
      if (!token) {
        setLoading(false);
        return;
      }
      
      // ⭐ 토큰이 명백히 만료된 경우 즉시 정리
      if (isTokenExpired(token)) {
        console.log('🔒 토큰 만료됨, 로그아웃');
        clearAuth();
        setLoading(false);
        return;
      }
      
      // ⭐ 토큰이 유효해 보이면 UI는 이미 로그인 상태로 표시
      // 백그라운드에서 서버 검증 진행
      try {
        await fetchUser(true); // silent mode
      } catch (error) {
        // 검증 실패 시에만 로그아웃
        console.warn('토큰 검증 실패');
      }
      
      setLoading(false);
    };

    initAuth();
    
    return () => {
      if (tokenRefreshTimer.current) {
        clearTimeout(tokenRefreshTimer.current);
      }
    };
  }, [isTokenExpired, clearAuth, fetchUser]);

  // ===========================================
  // 로그인
  // ===========================================
  const login = useCallback(async (username, password) => {
    try {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      const response = await axios.post(endpoints.auth.login, formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      const { access_token } = response.data;
      
      // 토큰 저장
      localStorage.setItem('token', access_token);
      localStorage.setItem('username', username);
      
      // 즉시 인증 상태 설정 (깜빡임 방지)
      setIsAuthenticated(true);
      
      // 사용자 정보 로드
      await fetchUser();

      console.log('✅ 로그인 성공');
      return { success: true };
    } catch (error) {
      console.error('❌ 로그인 실패:', error);
      const message = error.response?.data?.detail || '로그인에 실패했습니다.';
      return { success: false, error: message };
    }
  }, [fetchUser]);

  // ===========================================
  // 회원가입
  // ===========================================
  const register = useCallback(async (username, password) => {
    try {
      await axios.post(endpoints.auth.register, { username, password });
      return { success: true };
    } catch (error) {
      console.error('❌ 회원가입 실패:', error);
      const message = error.response?.data?.detail || '회원가입에 실패했습니다.';
      return { success: false, error: message };
    }
  }, []);

  // ===========================================
  // 아이디 중복 검사
  // ===========================================
  const checkUsername = useCallback(async (username) => {
    try {
      const response = await axios.get(`${endpoints.auth.register.replace('/register', '')}/check-username/${username}`);
      return response.data;
    } catch (error) {
      console.error('아이디 중복 검사 실패:', error);
      return { username, available: true };
    }
  }, []);

  // ===========================================
  // 로그아웃
  // ===========================================
  const logout = useCallback(() => {
    console.log('👋 로그아웃');
    clearAuth();
  }, [clearAuth]);

  const value = {
    user,
    isAuthenticated,
    loading,
    login,
    register,
    logout,
    fetchUser,
    checkUsername,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;