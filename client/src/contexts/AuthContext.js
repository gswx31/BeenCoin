// client/src/contexts/AuthContext.js
// =============================================================================
// 인증 Context - 새로고침 깜빡임 완전 해결 버전
// =============================================================================
// 
// 📌 주요 변경점:
// 1. localStorage에서 user 정보 즉시 복원 (초기 렌더링 시 로그인 상태 유지)
// 2. JWT 토큰 만료 시간 클라이언트에서 미리 체크
// 3. 백그라운드에서 조용히 토큰 검증 (silent mode)
// 4. 토큰 자동 갱신 스케줄링 (옵션)
//
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
  // ============================================================
  // ⭐ 핵심 개선 1: 초기 상태를 localStorage에서 즉시 복원
  // ============================================================
  const [user, setUser] = useState(() => {
    try {
      const savedUser = localStorage.getItem('user');
      return savedUser ? JSON.parse(savedUser) : null;
    } catch {
      return null;
    }
  });
  
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    const token = localStorage.getItem('token');
    if (!token) return false;
    
    // 토큰 만료 여부 빠르게 체크
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp * 1000 > Date.now();
    } catch {
      return false;
    }
  });
  
  // ⭐ 핵심 개선 2: 토큰이 있고 유효해 보이면 loading을 false로 시작
  const [loading, setLoading] = useState(() => {
    const token = localStorage.getItem('token');
    if (!token) return false;
    
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      // 토큰이 만료되지 않았으면 로딩 없이 시작
      return payload.exp * 1000 <= Date.now();
    } catch {
      return true; // 파싱 실패하면 검증 필요
    }
  });
  
  const isValidating = useRef(false);
  const tokenRefreshTimer = useRef(null);

  // ============================================================
  // JWT 토큰 디코딩
  // ============================================================
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

  // ============================================================
  // 토큰 만료 체크
  // ============================================================
  const isTokenExpired = useCallback((token) => {
    const payload = decodeToken(token);
    if (!payload || !payload.exp) return true;
    // 30초 여유를 두고 만료 체크
    return payload.exp * 1000 < Date.now() + 30000;
  }, [decodeToken]);

  // ============================================================
  // 인증 정보 초기화
  // ============================================================
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

  // ============================================================
  // 사용자 정보 조회 (백그라운드 검증)
  // ============================================================
  const fetchUser = useCallback(async (silent = false) => {
    if (isValidating.current) return null;
    isValidating.current = true;
    
    try {
      const response = await axios.get(endpoints.auth.me);
      const userData = response.data;
      
      setUser(userData);
      setIsAuthenticated(true);
      
      // ⭐ 사용자 정보 localStorage에 저장 (새로고침 시 즉시 복원용)
      localStorage.setItem('user', JSON.stringify(userData));
      
      if (userData.username) {
        localStorage.setItem('username', userData.username);
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
  }, [clearAuth]);

  // ============================================================
  // ⭐ 앱 시작 시 토큰 검증 (깜빡임 없이)
  // ============================================================
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('token');
      
      if (!token) {
        setLoading(false);
        return;
      }
      
      // 토큰이 명백히 만료된 경우 즉시 정리
      if (isTokenExpired(token)) {
        console.log('🔒 토큰 만료됨, 로그아웃');
        clearAuth();
        setLoading(false);
        return;
      }
      
      // ⭐ 핵심: 토큰이 유효해 보이면 UI는 이미 로그인 상태
      // 백그라운드에서 조용히 서버 검증만 진행
      try {
        await fetchUser(true); // silent mode - 에러 로그 안 찍음
      } catch (error) {
        // 검증 실패해도 이미 clearAuth 호출됨
        console.warn('토큰 검증 실패 (백그라운드)');
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

  // ============================================================
  // 로그인
  // ============================================================
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
      
      // ⭐ 즉시 인증 상태 설정 (깜빡임 방지)
      setIsAuthenticated(true);
      
      // 사용자 정보 로드 & 저장
      const userData = await fetchUser();
      
      console.log('✅ 로그인 성공');
      return { success: true, user: userData };
    } catch (error) {
      console.error('❌ 로그인 실패:', error);
      const message = error.response?.data?.detail || '로그인에 실패했습니다.';
      return { success: false, error: message };
    }
  }, [fetchUser]);

  // ============================================================
  // 회원가입
  // ============================================================
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

  // ============================================================
  // 아이디 중복 검사
  // ============================================================
  const checkUsername = useCallback(async (username) => {
    try {
      const response = await axios.get(
        `${endpoints.auth.register.replace('/register', '')}/check-username/${username}`
      );
      return response.data;
    } catch (error) {
      return { username, available: true };
    }
  }, []);

  // ============================================================
  // 로그아웃
  // ============================================================
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