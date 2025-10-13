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

  const checkAuth = () => {
    const token = localStorage.getItem('token');
    const username = localStorage.getItem('username');
    
    if (token && username) {
      setUser({ username });
      setIsAuthenticated(true);
    }
    setLoading(false);
  };

// client/src/contexts/AuthContext.js
const login = async (username, password) => {
  try {
    console.log('Sending login request with:', { username, password }); // 디버깅용
    
    const response = await fetch('http://localhost:8000/api/v1/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',  // JSON 헤더 명시
      },
      body: JSON.stringify({
        username: username,
        password: password
      }),
    });
    
    console.log('Response status:', response.status); // 디버깅용
    
    if (!response.ok) {
      // 422 에러일 경우 상세 정보 확인
      if (response.status === 422) {
        const errorData = await response.json();
        console.error('Validation error:', errorData);
        throw new Error('Invalid data format');
      }
      // 401 에러 (잘못된 credentials)
      if (response.status === 401) {
        throw new Error('Invalid username or password');
      }
      throw new Error(`Login failed: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Login success:', data); // 디버깅용
    
    // 토큰 저장
    localStorage.setItem('token', data.access_token);
    setUser({ username: username }); // 또는 백엔드에서 user 정보를 반환한다면 data.user 사용
    return true;
  } catch (error) {
    console.error('Login error:', error);
    return false;
  }
};

  const register = async (username, password) => {
    try {
      await axios.post('/api/v1/auth/register', { username, password });
      toast.success('회원가입 성공! 로그인해주세요.');
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || '회원가입에 실패했습니다.');
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