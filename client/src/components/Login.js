import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post('/api/v1/auth/login', { username, password });
      localStorage.setItem('token', response.data.access_token);
      toast.success('로그인 성공!');
      navigate('/dashboard');
    } catch (error) {
      toast.error('로그인 실패: ' + (error.response?.data?.detail || '오류 발생'));
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10 p-6 bg-white rounded-lg shadow-xl">
      <h2 className="text-2xl font-bold mb-4 text-center">로그인</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="text"
          placeholder="아이디"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-accent"
        />
        <input
          type="password"
          placeholder="비밀번호"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-accent"
        />
        <button type="submit" className="w-full p-2 bg-accent text-white rounded hover:bg-teal-600">
          로그인
        </button>
      </form>
      <p className="mt-4 text-center">
        계정이 없으신가요? <a href="/register" className="text-accent hover:underline">회원가입</a>
      </p>
    </div>
  );
};

export default Login;
