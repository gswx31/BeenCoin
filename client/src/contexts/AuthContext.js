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

  const login = async (username, password) => {
    try {
      console.log('Login attempt:', username);
      
      // OAuth2 형식으로 form-data 전송
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      const response = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData.toString(),
      });
      
      console.log('Login response status:', response.status);
      
      if (!response.ok) {
        const errorData = await response.json();
        console.error('Login error:', errorData);
        throw new Error(errorData.detail || 'Login failed');
      }
      
      const data = await response.json();
      console.log('Login successful:', data);
      
      // 토큰 및 사용자 정보 저장
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('username', data.username || username);
      
      setUser({ username: data.username || username });
      setIsAuthenticated(true);
      
      toast.success('로그인 성공!');
      return true;
      
    } catch (error) {
      console.error('Login error:', error);
      toast.error(error.message || '로그인에 실패했습니다.');
      return false;
    }
  };

  const register = async (username, password) => {
    try {
      console.log('Register attempt:', username);
      
      const response = await axios.post('/api/v1/auth/register', { 
        username, 
        password 
      });
      
      console.log('Register successful:', response.data);
      toast.success('회원가입 성공! 로그인해주세요.');
      return true;
      
    } catch (error) {
      console.error('Register error:', error);
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