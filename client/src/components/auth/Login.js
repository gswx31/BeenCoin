// client/src/components/auth/Login.js
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuth();

  // 리다이렉트 처리
  const from = location.state?.from?.pathname || '/';

  // 이미 로그인된 사용자 처리
  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  const validateForm = () => {
    if (!username.trim()) {
      return false;
    }
    if (!password) {
      return false;
    }
    return true;
  };

  const handleSubmit = () => {
    if (loading) return;

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    login(username, password)
      .then((success) => {
        if (success) {
          // AuthContext에서 toast.success 이미 처리됨
          setTimeout(() => {
            navigate(from, { replace: true });
          }, 1000);
        }
        // 실패 시 AuthContext에서 toast.error 이미 처리됨
        // 로컬 에러 상태 제거: toast로 충분하니 UI 에러 박스 생략
        console.log('Login attempt finished. Username still:', username); // 디버그: 값 유지 확인
      })
      .catch((unexpectedError) => {
        console.error('Unexpected error in handleSubmit:', unexpectedError);
        // 예상치 못한 에러 시 별도 처리 (toast는 Context에서 안 잡힘)
        // 필요 시 추가 toast나 alert
      })
      .finally(() => {
        setLoading(false);
      });
  };

  // 엔터 키 처리 (onKeyDown으로 변경: React 권장, onKeyPress는 deprecated)
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !loading) {
      handleSubmit();
    }
  };

  return (
    <div className="max-w-md mx-auto mt-20">
      <div className="bg-gray-800 rounded-lg shadow-xl p-8">
        <h2 className="text-3xl font-bold mb-6 text-center">로그인</h2>
        
        {/* 에러 메시지 표시 제거: AuthContext의 toast로 대체
        {error && (
          <div className="mb-4 p-3 bg-red-900 border border-red-700 text-red-200 rounded-lg animate-pulse">
            <div className="flex items-center">
              <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              {error}
            </div>
          </div>
        )} */}
        
        {/* form 태그 제거: 페이지 리로드 방지. div로 대체하고 onClick/onKeyDown으로 submit */}
        <div className="space-y-4">
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
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-300"
                disabled={loading}
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
          
          <button
            type="button"  // type="submit" 제거: 폼 없으니 button 클릭으로만 동작
            onClick={handleSubmit}
            disabled={loading}
            className="w-full py-3 bg-accent text-white rounded-lg hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed font-semibold transition-colors duration-200 transform hover:scale-[1.02] active:scale-[0.98]"
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
        </div>
        
        {/* 추가 기능들 */}
        <div className="mt-6 space-y-3">
          <div className="text-center">
            <a href="/register" className="text-accent hover:underline text-sm">
              계정이 없으신가요? 회원가입
            </a>
          </div>
          <div className="text-center">
            <button className="text-gray-400 hover:text-gray-300 text-xs">
              비밀번호를 잊어버리셨나요?
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;