// client/src/contexts/AuthContext.js
// =============================================================================
// 인증 Context - 새로고침 시 로그인 유지 수정
// =============================================================================
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
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
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  // ===========================================
  // 앱 시작 시 토큰 확인
  // ===========================================
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('token');
      
      if (token) {
        console.log('🔑 저장된 토큰 발견, 유효성 검증 중...');
        try {
          await fetchUser();
        } catch (error) {
          console.error('토큰 검증 실패:', error);
          // 토큰이 유효하지 않으면 정리
          clearAuth();
        }
      } else {
        console.log('🔓 저장된 토큰 없음');
      }
      
      setLoading(false);
    };

    initAuth();
  }, []);

  // ===========================================
  // 인증 정보 초기화
  // ===========================================
  const clearAuth = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  // ===========================================
  // 사용자 정보 조회 (/me 엔드포인트)
  // ===========================================
  const fetchUser = useCallback(async () => {
    try {
      const response = await axios.get(endpoints.auth.me);
      console.log('✅ 사용자 정보 조회 성공:', response.data);
      
      setUser(response.data);
      setIsAuthenticated(true);
      
      // username도 저장 (백업)
      if (response.data.username) {
        localStorage.setItem('username', response.data.username);
      }
      
      return response.data;
    } catch (error) {
      console.error('❌ 사용자 정보 조회 실패:', error);
      
      // 401/403 에러면 토큰 만료
      if (error.response?.status === 401 || error.response?.status === 403) {
        clearAuth();
      }
      
      throw error;
    }
  }, [clearAuth]);

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
      
      // ⭐ 토큰 저장 (핵심!)
      localStorage.setItem('token', access_token);
      localStorage.setItem('username', username);
      
      console.log('✅ 로그인 성공, 토큰 저장됨');

      // 사용자 정보 로드
      await fetchUser();

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
  // ⭐ 아이디 중복 검사 (NEW)
  // ===========================================
  const checkUsername = useCallback(async (username) => {
    try {
      const response = await axios.get(`${endpoints.auth.register.replace('/register', '')}/check-username/${username}`);
      return response.data; // { username, available: true/false }
    } catch (error) {
      console.error('아이디 중복 검사 실패:', error);
      return { username, available: true }; // 에러 시 일단 통과
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
    checkUsername,  // ⭐ NEW
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;