// client/src/components/auth/Login.js
// =============================================================================
// 로그인 컴포넌트 - 보안 강화 버전
// =============================================================================
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');

  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuth();

  // 이전 페이지 또는 대시보드로 리다이렉트
  const from = location.state?.from?.pathname || '/';

  // 이미 로그인된 경우 리다이렉트
  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  // 폼 유효성 검증
  const validateForm = () => {
    if (!username.trim()) {
      setError('아이디를 입력해주세요.');
      return false;
    }
    if (!password) {
      setError('비밀번호를 입력해주세요.');
      return false;
    }
    return true;
  };

  // 로그인 제출
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!validateForm()) return;
    if (loading) return;

    setLoading(true);

    const success = await login(username, password);

    if (success) {
      // 잠시 후 리다이렉트 (토스트 표시를 위해)
      setTimeout(() => navigate(from, { replace: true }), 500);
    } else {
      // 로그인 실패 - 입력값은 유지
      setError('아이디 또는 비밀번호가 올바르지 않습니다.');
    }

    setLoading(false);
  };

  // 엔터 키 처리
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !loading) {
      handleSubmit(e);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-20">
      <div className="bg-gray-800 rounded-lg shadow-xl p-8">
        {/* 로고 및 제목 */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-accent rounded-lg flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl font-bold">₿</span>
          </div>
          <h2 className="text-3xl font-bold">로그인</h2>
          <p className="text-gray-400 mt-2">BeenCoin 모의투자에 오신 것을 환영합니다</p>
        </div>

        {/* 에러 메시지 */}
        {error && (
          <div className="mb-6 p-4 bg-red-900 bg-opacity-50 border border-red-700 text-red-200 rounded-lg">
            <div className="flex items-center">
              <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
              {error}
            </div>
          </div>
        )}

        {/* 로그인 폼 */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 아이디 입력 */}
          <div>
            <label htmlFor="username" className="block text-sm font-medium mb-2">
              아이디
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                setError('');
              }}
              onKeyDown={handleKeyDown}
              className="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent transition-colors"
              placeholder="아이디를 입력하세요"
              disabled={loading}
              autoComplete="username"
              autoFocus
            />
          </div>

          {/* 비밀번호 입력 */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium mb-2">
              비밀번호
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setError('');
                }}
                onKeyDown={handleKeyDown}
                className="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent transition-colors pr-12"
                placeholder="비밀번호를 입력하세요"
                disabled={loading}
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
              >
                {showPassword ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* 로그인 버튼 */}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-accent text-white rounded-lg hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed font-semibold transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98]"
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                로그인 중...
              </span>
            ) : (
              '로그인'
            )}
          </button>
        </form>

        {/* 회원가입 링크 */}
        <p className="mt-8 text-center text-gray-400">
          계정이 없으신가요?{' '}
          <Link to="/register" className="text-accent hover:underline font-semibold">
            회원가입
          </Link>
        </p>

        {/* 모의투자 안내 */}
        <div className="mt-6 p-4 bg-blue-900 bg-opacity-30 border border-blue-700 rounded-lg text-sm text-blue-200">
          <p className="flex items-center">
            <span className="mr-2">ℹ️</span>
            이 플랫폼은 모의투자 서비스입니다. 실제 돈이 거래되지 않습니다.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;