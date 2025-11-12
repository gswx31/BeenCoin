// client/src/components/layout/Header.js
import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const Header = () => {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="bg-gray-800 border-b border-gray-700">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* 로고 */}
          <Link to="/" className="flex items-center space-x-2">
            <div className="w-10 h-10 bg-accent rounded-lg flex items-center justify-center">
              <span className="text-2xl font-bold">₿</span>
            </div>
            <span className="text-xl font-bold">BeenCoin</span>
          </Link>

          {/* 네비게이션 */}
          <nav className="flex items-center space-x-6">
            <Link to="/" className="hover:text-accent transition-colors">
              마켓
            </Link>
            {isAuthenticated && (
              <>
                <Link to="/portfolio" className="hover:text-accent transition-colors">
                  포트폴리오
                </Link>
              </>
            )}
          </nav>

          {/* 사용자 메뉴 */}
          <div className="flex items-center space-x-4">
            {isAuthenticated ? (
              <>
                <span className="text-gray-400">
                  환영합니다, <span className="text-white font-semibold">{user.username}</span>님
                </span>
                <button
                  onClick={handleLogout}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
                >
                  로그아웃
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="px-4 py-2 hover:text-accent transition-colors"
                >
                  로그인
                </Link>
                <Link
                  to="/register"
                  className="px-4 py-2 bg-accent hover:bg-teal-600 rounded-lg transition-colors"
                >
                  회원가입
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;