// client/src/contexts/AuthContext.js
import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from '../api/axios';
import { toast } from 'react-toastify';

const AuthContext = createContext();

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

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('token');
    
    if (token) {
      try {
        // 토큰 유효성 검증
        const response = await axios.get('/api/v1/auth/me');
        setUser(response.data);
        setIsAuthenticated(true);
      } catch (error) {
        console.error('Token validation failed:', error);
        // 토큰이 유효하지 않으면 제거
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        setUser(null);
        setIsAuthenticated(false);
      }
    }
    
    setLoading(false);
  };

  // client/src/contexts/AuthContext.js
  const login = async (username, password) => {
    try {
      console.log('🔐 Login attempt:', username);
      
      // 입력값 검증
      if (!username.trim() || !password.trim()) {
        toast.error('아이디와 비밀번호를 입력해주세요.');
        return false;
      }

      // FormData 형식으로 로그인
      const formData = new URLSearchParams();
      formData.append('username', username.trim());
      formData.append('password', password);

      // 로딩 상태를 위해 약간의 지연 추가 (UX 향상)
      await new Promise(resolve => setTimeout(resolve, 500));

      const response = await axios.post('/api/v1/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        timeout: 10000, // 10초 타임아웃
      });

      console.log('✅ Login successful:', response.data);

      const { access_token, username: returnedUsername } = response.data;

      // 토큰 저장
      localStorage.setItem('token', access_token);
      localStorage.setItem('username', returnedUsername);

      // 사용자 정보 설정
      setUser({ username: returnedUsername });
      setIsAuthenticated(true);

      toast.success(`환영합니다, ${returnedUsername}님! 🎉`);
      return true;

    } catch (error) {
      console.error('❌ Login error:', error);

      // 에러 타입에 따른 상세 메시지
      let errorMessage = '로그인에 실패했습니다.';

      if (error.code === 'ECONNABORTED' || !error.response) {
        errorMessage = '서버 연결에 실패했습니다. 네트워크를 확인해주세요.';
      } else if (error.response.status === 401) {
        errorMessage = '아이디 또는 비밀번호가 올바르지 않습니다.';
      } else if (error.response.status === 422) {
        errorMessage = '입력 형식이 올바르지 않습니다.';
      } else if (error.response.status >= 500) {
        errorMessage = '서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
      } else if (error.response.data?.detail) {
        errorMessage = error.response.data.detail;
      }

      // 토스트 알림 지속 시간 증가 (기본 5초)
      toast.error(errorMessage, {
        autoClose: 5000,
        pauseOnHover: true,
      });

      return false;
    }
  };
  const register = async (username, password) => {
    try {
      console.log('📝 Register attempt:', username);
      
      const response = await axios.post('/api/v1/auth/register', { 
        username, 
        password 
      });
      
      console.log('✅ Register successful:', response.data);
      toast.success('회원가입 성공! 로그인해주세요.');
      return true;
      
    } catch (error) {
      console.error('❌ Register error:', error);
      const errorMsg = error.response?.data?.detail || '회원가입에 실패했습니다.';
      toast.error(errorMsg);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    setUser(null);
    setIsAuthenticated(false);
    toast.info('로그아웃되었습니다.');
  };

  const value = {
    user,
    isAuthenticated,
    loading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};