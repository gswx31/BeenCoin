// client/src/components/auth/Login.js (주요 변경: 로컬 error 상태 추가, handleSubmit 개선)
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState(''); // 추가: 로컬 에러 상태 (toast와 병행, 입력 유지 보장)
  
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuth();

  const from = location.state?.from?.pathname || '/';

  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  const validateForm = () => {
    if (!username.trim() || !password) return false;
    return true;
  };

  const handleSubmit = async (e) => {  // async로 변경: await 가능하게
    e.preventDefault(); // ✅ 이거 없으면 새로고침됩니다.
    if (loading || !validateForm()) return;

    setLoading(true);
    setLocalError(''); // 에러 초기화

    const success = await login(username, password); // await으로 동기적으로 처리

    if (success) {
      // 성공 시 navigate (Context에서 toast 이미 처리)
      setTimeout(() => navigate(from, { replace: true }), 1000);
    } else {
      // 실패 시 로컬 에러 설정 (입력 필드 유지, toast는 Context에서)
      setLocalError('로그인 실패. 다시 시도해주세요.'); // 옵션: toast 대신 또는 병행
      console.log('Login failed, inputs preserved:', { username, password }); // 디버그: 값 유지 확인
      alert('로그인에 실패했습니다. 아이디와 비밀번호를 확인해주세요.'); // 추가: alert로 즉각 알림
    }

    setLoading(false); // finally 대신 직접
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !loading) handleSubmit();
  };

  return (
    <div className="max-w-md mx-auto mt-20">
      <div className="bg-gray-800 rounded-lg shadow-xl p-8">
        <h2 className="text-3xl font-bold mb-6 text-center">로그인</h2>
        
        {/* 로컬 에러 표시 추가: toast가 사라져도 입력란 아래에 유지 */}
        {localError && (
          <div className="mb-4 p-3 bg-red-900 border border-red-700 text-red-200 rounded-lg animate-pulse">
            {localError}
          </div>
        )}
        
        <div className="space-y-4">
          {/* 입력 필드 동일, 하지만 리렌더링 시 상태 유지 보장 */}
          <div>
            <label className="block text-sm font-medium mb-2">아이디</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent transition-colors"
              placeholder="아이디를 입력하세요"
              disabled={loading}
              autoComplete="username"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">비밀번호</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent transition-colors pr-10"
                placeholder="비밀번호를 입력하세요"
                disabled={loading}
                autoComplete="current-password"
              />
              {/* 버튼 동일 */}
            </div>
          </div>
          
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="w-full py-3 bg-accent text-white rounded-lg hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed font-semibold transition-colors duration-200 transform hover:scale-[1.02] active:scale-[0.98]"
          >
            {loading ? '로그인 중...' : '로그인'}
          </button>
        </div>
        
        {/* 나머지 동일 */}
      </div>
    </div>
  );
};

export default Login;