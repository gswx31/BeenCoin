// client/src/components/auth/Register.js
// =============================================================================
// 회원가입 컴포넌트 - 실시간 아이디 중복 검사 추가
// =============================================================================
import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { toast } from 'react-toastify';

const Register = () => {
  const navigate = useNavigate();
  const { register, checkUsername, isAuthenticated } = useAuth();

  const [formData, setFormData] = useState({
    username: '',
    password: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  
  // ⭐ 아이디 중복 검사 상태
  const [usernameStatus, setUsernameStatus] = useState({
    checking: false,
    available: null,
    message: '',
  });

  // 이미 로그인된 경우 리다이렉트
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  // ===========================================
  // ⭐ 아이디 중복 검사 (디바운스 적용)
  // ===========================================
  useEffect(() => {
    const username = formData.username.trim();
    
    // 빈 값이거나 너무 짧으면 검사 안 함
    if (!username || username.length < 3) {
      setUsernameStatus({
        checking: false,
        available: null,
        message: username.length > 0 ? '아이디는 3자 이상이어야 합니다.' : '',
      });
      return;
    }

    // 영문, 숫자, 밑줄만 허용
    if (!/^[a-zA-Z0-9_]+$/.test(username)) {
      setUsernameStatus({
        checking: false,
        available: false,
        message: '영문, 숫자, 밑줄(_)만 사용 가능합니다.',
      });
      return;
    }

    // 디바운스: 500ms 후에 검사
    setUsernameStatus(prev => ({ ...prev, checking: true, message: '확인 중...' }));
    
    const timer = setTimeout(async () => {
      try {
        const result = await checkUsername(username);
        setUsernameStatus({
          checking: false,
          available: result.available,
          message: result.available ? '사용 가능한 아이디입니다.' : '이미 사용 중인 아이디입니다.',
        });
      } catch (error) {
        setUsernameStatus({
          checking: false,
          available: null,
          message: '중복 확인 중 오류가 발생했습니다.',
        });
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [formData.username, checkUsername]);

  // ===========================================
  // 입력 변경 핸들러
  // ===========================================
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
    
    // 에러 초기화
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: '',
      }));
    }
  };

  // ===========================================
  // 폼 유효성 검사
  // ===========================================
  const validate = () => {
    const newErrors = {};

    if (!formData.username.trim()) {
      newErrors.username = '아이디를 입력해주세요.';
    } else if (formData.username.length < 3) {
      newErrors.username = '아이디는 3자 이상이어야 합니다.';
    } else if (usernameStatus.available === false) {
      newErrors.username = '이미 사용 중인 아이디입니다.';
    }

    if (!formData.password) {
      newErrors.password = '비밀번호를 입력해주세요.';
    } else if (formData.password.length < 6) {
      newErrors.password = '비밀번호는 6자 이상이어야 합니다.';
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = '비밀번호 확인을 입력해주세요.';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = '비밀번호가 일치하지 않습니다.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // ===========================================
  // 회원가입 제출
  // ===========================================
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validate()) return;
    
    // 중복 검사 진행 중이면 대기
    if (usernameStatus.checking) {
      toast.warning('아이디 중복 확인 중입니다. 잠시 후 다시 시도해주세요.');
      return;
    }

    // 중복된 아이디면 차단
    if (usernameStatus.available === false) {
      toast.error('이미 사용 중인 아이디입니다.');
      return;
    }

    setLoading(true);

    const result = await register(formData.username, formData.password);

    if (result.success) {
      toast.success('회원가입이 완료되었습니다! 로그인해주세요.');
      navigate('/login');
    } else {
      toast.error(result.error);
    }

    setLoading(false);
  };

  return (
    <div className="max-w-md mx-auto">
      <div className="bg-gray-800 rounded-lg p-8 shadow-lg">
        <h1 className="text-2xl font-bold text-center mb-6">회원가입</h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 아이디 */}
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-300 mb-1">
              아이디
            </label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              className={`w-full px-4 py-3 bg-gray-700 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 ${
                errors.username 
                  ? 'border-red-500' 
                  : usernameStatus.available === true 
                    ? 'border-green-500' 
                    : usernameStatus.available === false 
                      ? 'border-red-500' 
                      : 'border-gray-600'
              }`}
              placeholder="영문, 숫자, 밑줄 3자 이상"
            />
            
            {/* ⭐ 실시간 중복 검사 상태 표시 */}
            {formData.username && (
              <div className={`mt-1 text-sm flex items-center ${
                usernameStatus.checking 
                  ? 'text-yellow-400' 
                  : usernameStatus.available === true 
                    ? 'text-green-400' 
                    : usernameStatus.available === false 
                      ? 'text-red-400' 
                      : 'text-gray-400'
              }`}>
                {usernameStatus.checking && (
                  <svg className="animate-spin h-4 w-4 mr-1" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                )}
                {usernameStatus.available === true && (
                  <svg className="h-4 w-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                )}
                {usernameStatus.available === false && (
                  <svg className="h-4 w-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                )}
                {usernameStatus.message}
              </div>
            )}
            
            {errors.username && !usernameStatus.message && (
              <p className="mt-1 text-sm text-red-400">{errors.username}</p>
            )}
          </div>

          {/* 비밀번호 */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-1">
              비밀번호
            </label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              className={`w-full px-4 py-3 bg-gray-700 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 ${
                errors.password ? 'border-red-500' : 'border-gray-600'
              }`}
              placeholder="6자 이상"
            />
            {errors.password && (
              <p className="mt-1 text-sm text-red-400">{errors.password}</p>
            )}
          </div>

          {/* 비밀번호 확인 */}
          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-300 mb-1">
              비밀번호 확인
            </label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              className={`w-full px-4 py-3 bg-gray-700 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 ${
                errors.confirmPassword ? 'border-red-500' : 'border-gray-600'
              }`}
              placeholder="비밀번호 재입력"
            />
            {errors.confirmPassword && (
              <p className="mt-1 text-sm text-red-400">{errors.confirmPassword}</p>
            )}
            
            {/* 비밀번호 일치 확인 */}
            {formData.confirmPassword && formData.password === formData.confirmPassword && (
              <p className="mt-1 text-sm text-green-400 flex items-center">
                <svg className="h-4 w-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                비밀번호가 일치합니다.
              </p>
            )}
          </div>

          {/* 제출 버튼 */}
          <button
            type="submit"
            disabled={loading || usernameStatus.checking || usernameStatus.available === false}
            className={`w-full py-3 rounded-lg font-semibold transition-colors ${
              loading || usernameStatus.checking || usernameStatus.available === false
                ? 'bg-gray-600 cursor-not-allowed'
                : 'bg-teal-600 hover:bg-teal-700'
            }`}
          >
            {loading ? '처리 중...' : '회원가입'}
          </button>
        </form>

        {/* 로그인 링크 */}
        <p className="text-center text-gray-400 mt-6">
          이미 계정이 있으신가요?{' '}
          <Link to="/login" className="text-teal-400 hover:text-teal-300">
            로그인
          </Link>
        </p>
      </div>
    </div>
  );
};

export default Register;