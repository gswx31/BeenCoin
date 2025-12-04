// client/src/components/auth/Login.js
// =============================================================================
// 로그인 컴포넌트
// =============================================================================
import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { toast } from 'react-toastify';

const Login = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuth();

  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  // 이전 페이지로 리다이렉트할 경로
  const from = location.state?.from?.pathname || '/';

  // 이미 로그인된 경우 리다이렉트
  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

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
    }

    if (!formData.password) {
      newErrors.password = '비밀번호를 입력해주세요.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // ===========================================
  // 로그인 제출
  // ===========================================
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validate()) return;

    setLoading(true);

    const result = await login(formData.username, formData.password);

    if (result.success) {
      toast.success('로그인 성공!');
      navigate(from, { replace: true });
    } else {
      toast.error(result.error);
    }

    setLoading(false);
  };

  return (
    <div className="max-w-md mx-auto">
      <div className="bg-gray-800 rounded-lg p-8 shadow-lg">
        <h1 className="text-2xl font-bold text-center mb-6">로그인</h1>

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
                errors.username ? 'border-red-500' : 'border-gray-600'
              }`}
              placeholder="아이디 입력"
              autoComplete="username"
            />
            {errors.username && (
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
              placeholder="비밀번호 입력"
              autoComplete="current-password"
            />
            {errors.password && (
              <p className="mt-1 text-sm text-red-400">{errors.password}</p>
            )}
          </div>

          {/* 제출 버튼 */}
          <button
            type="submit"
            disabled={loading}
            className={`w-full py-3 rounded-lg font-semibold transition-colors ${
              loading
                ? 'bg-gray-600 cursor-not-allowed'
                : 'bg-teal-600 hover:bg-teal-700'
            }`}
          >
            {loading ? '로그인 중...' : '로그인'}
          </button>
        </form>

        {/* 회원가입 링크 */}
        <p className="text-center text-gray-400 mt-6">
          계정이 없으신가요?{' '}
          <Link to="/register" className="text-teal-400 hover:text-teal-300">
            회원가입
          </Link>
        </p>

        {/* 테스트 계정 안내 */}
        <div className="mt-6 p-4 bg-gray-700 rounded-lg">
          <p className="text-sm text-gray-400 text-center mb-2">테스트 계정</p>
          <p className="text-xs text-gray-500 text-center">
            ID: testuser1 / PW: testpass123
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;