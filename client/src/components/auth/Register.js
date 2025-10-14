// client/src/components/auth/Register.js
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const Register = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { register } = useAuth();

  const validateForm = () => {
    // 아이디 검증
    if (username.length < 3) {
      setError('아이디는 3자 이상이어야 합니다.');
      return false;
    }
    if (username.length > 20) {
      setError('아이디는 20자 이하여야 합니다.');
      return false;
    }
    if (!/^[a-zA-Z0-9]+$/.test(username)) {
      setError('아이디는 영문자와 숫자만 사용 가능합니다.');
      return false;
    }

    // 비밀번호 검증
    if (password.length < 8) {
      setError('비밀번호는 8자 이상이어야 합니다.');
      return false;
    }
    if (password.length > 50) {
      setError('비밀번호는 50자 이하여야 합니다.');
      return false;
    }

    // 비밀번호 확인
    if (password !== confirmPassword) {
      setError('비밀번호가 일치하지 않습니다.');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // 폼 검증
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    console.log('회원가입 시도:', username);

    try {
      const success = await register(username, password);
      
      if (success) {
        console.log('회원가입 성공');
        navigate('/login');
      } else {
        setError('회원가입에 실패했습니다. 다시 시도해주세요.');
      }
    } catch (error) {
      console.error('회원가입 에러:', error);
      setError('회원가입 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-20">
      <div className="bg-gray-800 rounded-lg shadow-xl p-8">
        <h2 className="text-3xl font-bold mb-6 text-center">회원가입</h2>
        
        {/* 에러 메시지 */}
        {error && (
          <div className="mb-4 p-3 bg-red-900 border border-red-700 text-red-200 rounded-lg">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              아이디
              <span className="text-gray-400 text-xs ml-2">(3-20자, 영문/숫자)</span>
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                setError('');
              }}
              className="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent"
              placeholder="아이디를 입력하세요"
              required
              disabled={loading}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">
              비밀번호
              <span className="text-gray-400 text-xs ml-2">(8자 이상)</span>
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError('');
              }}
              className="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent"
              placeholder="비밀번호를 입력하세요"
              required
              disabled={loading}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">비밀번호 확인</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value);
                setError('');
              }}
              className="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent"
              placeholder="비밀번호를 다시 입력하세요"
              required
              disabled={loading}
            />
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-accent text-white rounded-lg hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed font-semibold transition-colors"
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                가입 중...
              </span>
            ) : (
              '가입하기'
            )}
          </button>
        </form>
        
        <p className="mt-6 text-center text-gray-400">
          이미 계정이 있으신가요?{' '}
          <a href="/login" className="text-accent hover:underline">
            로그인
          </a>
        </p>
      </div>
    </div>
  );
};

export default Register;