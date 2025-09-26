import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';

const Register = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/api/v1/auth/register', { username, password });
      toast.success('회원가입 성공! 로그인하세요.');
      navigate('/login');
    } catch (error) {
      toast.error('회원가입 실패: ' + (error.response?.data?.detail || '오류 발생'));
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10 p-6 bg-white rounded-lg shadow-xl">
      <h2 className="text-2xl font-bold mb-4 text-center">회원가입</h2>
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
          가입하기
        </button>
      </form>
      <p className="mt-4 text-center">
        이미 계정이 있으신가요? <a href="/login" className="text-accent hover:underline">로그인</a>
      </p>
    </div>
  );
};

export default Register;
