import React, { useState } from 'react';
import api from '../api';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-toastify';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post('/auth/login', { username, password });
      localStorage.setItem('token', data.access_token);
      toast.success('다시 만나서 반가워요! 🎉');
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || '로그인에 실패했어요 😢');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-900 px-4">
      <div className="w-full max-w-sm fade-in">
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">🪙</div>
          <h1 className="text-2xl font-bold text-white mb-1">빈코인</h1>
          <p className="text-muted text-sm">가상화폐 모의투자 시뮬레이터</p>
        </div>
        <div className="bg-dark-800 rounded-3xl p-8 border border-dark-600">
          <h2 className="text-lg font-semibold text-white mb-6 text-center">로그인</h2>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-muted text-xs font-medium mb-2">아이디</label>
              <input type="text" value={username} onChange={(e) => setUsername(e.target.value)}
                className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-2xl text-white placeholder-dark-500 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
                placeholder="아이디를 입력해주세요" required autoFocus />
            </div>
            <div>
              <label className="block text-muted text-xs font-medium mb-2">비밀번호</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-2xl text-white placeholder-dark-500 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
                placeholder="비밀번호를 입력해주세요" required />
            </div>
            <button type="submit" disabled={loading}
              className="w-full py-3 bg-accent text-white font-semibold rounded-2xl hover:bg-accent-hover active:scale-[0.98] transition-all disabled:opacity-50">
              {loading ? '로그인 중...' : '로그인'}
            </button>
          </form>
          <p className="mt-6 text-center text-muted text-sm">
            아직 계정이 없나요?{' '}
            <Link to="/register" className="text-accent hover:text-accent-hover font-medium">회원가입</Link>
          </p>
        </div>
        <p className="text-center text-dark-500 text-xs mt-6">💰 시작 자금 $1,000,000으로 모의투자!</p>
      </div>
    </div>
  );
};

export default Login;
