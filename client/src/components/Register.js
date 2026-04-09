import React, { useState } from 'react';
import api from '../api';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-toastify';

const Register = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (password !== confirmPassword) { toast.error('비밀번호가 일치하지 않아요!'); return; }
    setLoading(true);
    try {
      await api.post('/auth/register', { username, password });
      toast.success('회원가입 완료! 로그인해주세요 🎊');
      navigate('/login');
    } catch (error) {
      toast.error(error.response?.data?.detail || '회원가입에 실패했어요 😢');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-900 px-4">
      <div className="w-full max-w-sm fade-in">
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">🪙</div>
          <h1 className="text-2xl font-bold text-white mb-1">회원가입</h1>
          <p className="text-muted text-sm">$1,000,000 가상 자금으로 시작해요!</p>
        </div>
        <div className="bg-dark-800 rounded-3xl p-8 border border-dark-600">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-muted text-xs font-medium mb-2">아이디</label>
              <input type="text" value={username} onChange={(e) => setUsername(e.target.value)}
                className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-2xl text-white placeholder-dark-500 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
                placeholder="사용할 아이디" required autoFocus />
            </div>
            <div>
              <label className="block text-muted text-xs font-medium mb-2">비밀번호</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-2xl text-white placeholder-dark-500 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
                placeholder="8자 이상" required minLength={8} />
            </div>
            <div>
              <label className="block text-muted text-xs font-medium mb-2">비밀번호 확인</label>
              <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-2xl text-white placeholder-dark-500 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
                placeholder="다시 한번 입력" required minLength={8} />
            </div>
            <button type="submit" disabled={loading}
              className="w-full py-3 bg-accent text-white font-semibold rounded-2xl hover:bg-accent-hover active:scale-[0.98] transition-all disabled:opacity-50">
              {loading ? '가입 중...' : '시작하기 🚀'}
            </button>
          </form>
          <p className="mt-6 text-center text-muted text-sm">
            이미 계정이 있나요?{' '}
            <Link to="/login" className="text-accent hover:text-accent-hover font-medium">로그인</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;
