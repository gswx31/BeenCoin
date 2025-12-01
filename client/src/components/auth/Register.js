// client/src/components/auth/Register.js
// =============================================================================
// 회원가입 컴포넌트 - 비밀번호 강도 검증 포함
// =============================================================================
import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const Register = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [agreedToTerms, setAgreedToTerms] = useState(false);

  const navigate = useNavigate();
  const { register, isAuthenticated } = useAuth();

  // 이미 로그인된 경우 리다이렉트
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  // 비밀번호 강도 계산
  const passwordStrength = useMemo(() => {
    if (!password) return { score: 0, label: '', color: '' };

    let score = 0;
    const checks = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /\d/.test(password),
      special: /[!@#$%^&*(),.?":{}|<>]/.test(password),
    };

    Object.values(checks).forEach((passed) => {
      if (passed) score += 20;
    });

    let label, color;
    if (score < 40) {
      label = '매우 약함';
      color = 'bg-red-500';
    } else if (score < 60) {
      label = '약함';
      color = 'bg-orange-500';
    } else if (score < 80) {
      label = '보통';
      color = 'bg-yellow-500';
    } else if (score < 100) {
      label = '강함';
      color = 'bg-green-500';
    } else {
      label = '매우 강함';
      color = 'bg-emerald-500';
    }

    return { score, label, color, checks };
  }, [password]);

  // 폼 유효성 검증
  const validateForm = () => {
    // 아이디 검증
    if (!username || username.length < 3) {
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
    if (!password || password.length < 8) {
      setError('비밀번호는 8자 이상이어야 합니다.');
      return false;
    }
    if (passwordStrength.score < 80) {
      setError('비밀번호가 너무 약합니다. 대문자, 소문자, 숫자, 특수문자를 포함해주세요.');
      return false;
    }

    // 비밀번호 확인
    if (password !== confirmPassword) {
      setError('비밀번호가 일치하지 않습니다.');
      return false;
    }

    // 약관 동의
    if (!agreedToTerms) {
      setError('이용약관에 동의해주세요.');
      return false;
    }

    return true;
  };

  // 회원가입 제출
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!validateForm()) return;
    if (loading) return;

    setLoading(true);

    const success = await register(username, password);

    if (success) {
      navigate('/login');
    }

    setLoading(false);
  };

  return (
    <div className="max-w-md mx-auto mt-10 mb-10">
      <div className="bg-gray-800 rounded-lg shadow-xl p-8">
        {/* 제목 */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-accent rounded-lg flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl font-bold">₿</span>
          </div>
          <h2 className="text-3xl font-bold">회원가입</h2>
          <p className="text-gray-400 mt-2">무료로 모의투자를 시작하세요</p>
        </div>

        {/* 에러 메시지 */}
        {error && (
          <div className="mb-6 p-4 bg-red-900 bg-opacity-50 border border-red-700 text-red-200 rounded-lg">
            {error}
          </div>
        )}

        {/* 회원가입 폼 */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 아이디 입력 */}
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
              className="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent transition-colors"
              placeholder="아이디를 입력하세요"
              disabled={loading}
              autoComplete="username"
            />
            {username && (
              <p className={`text-xs mt-1 ${
                /^[a-zA-Z0-9]{3,20}$/.test(username) ? 'text-green-400' : 'text-red-400'
              }`}>
                {/^[a-zA-Z0-9]{3,20}$/.test(username) 
                  ? '✓ 사용 가능한 아이디입니다' 
                  : '✗ 3-20자, 영문/숫자만 가능'}
              </p>
            )}
          </div>

          {/* 비밀번호 입력 */}
          <div>
            <label className="block text-sm font-medium mb-2">
              비밀번호
              <span className="text-gray-400 text-xs ml-2">(8자 이상)</span>
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setError('');
                }}
                className="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent transition-colors pr-12"
                placeholder="비밀번호를 입력하세요"
                disabled={loading}
                autoComplete="new-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white"
              >
                {showPassword ? '🙈' : '👁️'}
              </button>
            </div>

            {/* 비밀번호 강도 표시 */}
            {password && (
              <div className="mt-2">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-gray-400">비밀번호 강도</span>
                  <span className={
                    passwordStrength.score >= 80 ? 'text-green-400' : 'text-yellow-400'
                  }>
                    {passwordStrength.label}
                  </span>
                </div>
                <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${passwordStrength.color} transition-all duration-300`}
                    style={{ width: `${passwordStrength.score}%` }}
                  />
                </div>
                
                {/* 체크리스트 */}
                <div className="grid grid-cols-2 gap-1 mt-2 text-xs">
                  <CheckItem passed={passwordStrength.checks?.length} label="8자 이상" />
                  <CheckItem passed={passwordStrength.checks?.uppercase} label="대문자 포함" />
                  <CheckItem passed={passwordStrength.checks?.lowercase} label="소문자 포함" />
                  <CheckItem passed={passwordStrength.checks?.number} label="숫자 포함" />
                  <CheckItem passed={passwordStrength.checks?.special} label="특수문자 포함" />
                </div>
              </div>
            )}
          </div>

          {/* 비밀번호 확인 */}
          <div>
            <label className="block text-sm font-medium mb-2">비밀번호 확인</label>
            <input
              type={showPassword ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value);
                setError('');
              }}
              className="w-full p-3 bg-gray-700 rounded-lg border border-gray-600 focus:outline-none focus:border-accent transition-colors"
              placeholder="비밀번호를 다시 입력하세요"
              disabled={loading}
              autoComplete="new-password"
            />
            {confirmPassword && (
              <p className={`text-xs mt-1 ${
                password === confirmPassword ? 'text-green-400' : 'text-red-400'
              }`}>
                {password === confirmPassword ? '✓ 비밀번호가 일치합니다' : '✗ 비밀번호가 일치하지 않습니다'}
              </p>
            )}
          </div>

          {/* 약관 동의 */}
          <div className="flex items-start">
            <input
              type="checkbox"
              id="terms"
              checked={agreedToTerms}
              onChange={(e) => {
                setAgreedToTerms(e.target.checked);
                setError('');
              }}
              className="mt-1 mr-3 w-4 h-4 accent-accent"
            />
            <label htmlFor="terms" className="text-sm text-gray-400">
              <span className="text-accent">이용약관</span> 및{' '}
              <span className="text-accent">개인정보처리방침</span>에 동의합니다.
              <br />
              <span className="text-xs">(모의투자 서비스이며, 실제 거래가 발생하지 않습니다)</span>
            </label>
          </div>

          {/* 가입 버튼 */}
          <button
            type="submit"
            disabled={loading || passwordStrength.score < 80 || password !== confirmPassword || !agreedToTerms}
            className="w-full py-3 bg-accent text-white rounded-lg hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed font-semibold transition-all duration-200"
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                가입 중...
              </span>
            ) : (
              '가입하기'
            )}
          </button>
        </form>

        {/* 로그인 링크 */}
        <p className="mt-8 text-center text-gray-400">
          이미 계정이 있으신가요?{' '}
          <Link to="/login" className="text-accent hover:underline font-semibold">
            로그인
          </Link>
        </p>

        {/* 혜택 안내 */}
        <div className="mt-6 p-4 bg-gradient-to-r from-purple-900 to-blue-900 bg-opacity-50 rounded-lg">
          <h3 className="font-semibold mb-2">🎁 가입 혜택</h3>
          <ul className="text-sm text-gray-300 space-y-1">
            <li>✓ 100만 달러 모의투자금 지급</li>
            <li>✓ 실시간 시세 기반 거래</li>
            <li>✓ 현물/선물 거래 모두 지원</li>
            <li>✓ 레버리지 최대 125배</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

// 체크 아이템 컴포넌트
const CheckItem = ({ passed, label }) => (
  <span className={passed ? 'text-green-400' : 'text-gray-500'}>
    {passed ? '✓' : '○'} {label}
  </span>
);

export default Register;