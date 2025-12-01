// client/src/components/layout/Header.js
// =============================================================================
// 헤더 컴포넌트 - 네비게이션 및 사용자 메뉴
// =============================================================================
import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useMarket } from '../../contexts/MarketContext';

const Header = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, user, logout } = useAuth();
  const { isConnected } = useMarket();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
    setMobileMenuOpen(false);
  };

  const isActive = (path) => {
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  return (
    <header className="bg-gray-800 border-b border-gray-700 sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* 로고 */}
          <Link to="/" className="flex items-center space-x-2">
            <div className="w-10 h-10 bg-accent rounded-lg flex items-center justify-center">
              <span className="text-2xl font-bold">₿</span>
            </div>
            <div>
              <span className="text-xl font-bold">BeenCoin</span>
              <span className="text-xs text-gray-400 block">모의투자</span>
            </div>
          </Link>

          {/* 데스크톱 네비게이션 */}
          <nav className="hidden md:flex items-center space-x-1">
            <NavLink to="/" active={isActive('/')} exact>
              마켓
            </NavLink>
            
            {isAuthenticated && (
              <>
                <NavLink to="/futures/BTCUSDT" active={location.pathname.startsWith('/futures/')}>
                  <span className="flex items-center">
                    선물거래
                    <span className="ml-1 px-1.5 py-0.5 bg-purple-600 rounded text-xs">NEW</span>
                  </span>
                </NavLink>
                
                <NavLink to="/portfolio" active={isActive('/portfolio')}>
                  현물 포트폴리오
                </NavLink>
                
                <NavLink to="/futures/portfolio" active={isActive('/futures/portfolio')}>
                  선물 포트폴리오
                </NavLink>
              </>
            )}
          </nav>

          {/* 우측 영역 */}
          <div className="hidden md:flex items-center space-x-4">
            {/* 연결 상태 표시 */}
            <div className="flex items-center space-x-2 text-sm">
              {isConnected ? (
                <span className="flex items-center text-green-400">
                  <span className="w-2 h-2 bg-green-400 rounded-full mr-1 animate-pulse"></span>
                  실시간
                </span>
              ) : (
                <span className="flex items-center text-yellow-400">
                  <span className="w-2 h-2 bg-yellow-400 rounded-full mr-1"></span>
                  연결 중
                </span>
              )}
            </div>

            {/* 사용자 메뉴 */}
            {isAuthenticated ? (
              <div className="flex items-center space-x-4">
                <span className="text-gray-400">
                  <span className="text-white font-semibold">{user?.username}</span>님
                </span>
                <button
                  onClick={handleLogout}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
                >
                  로그아웃
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
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
              </div>
            )}
          </div>

          {/* 모바일 메뉴 버튼 */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-lg hover:bg-gray-700 transition-colors"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              {mobileMenuOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>

        {/* 모바일 메뉴 */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-gray-700">
            <nav className="flex flex-col space-y-2">
              <MobileNavLink to="/" onClick={() => setMobileMenuOpen(false)}>
                마켓
              </MobileNavLink>
              
              {isAuthenticated && (
                <>
                  <MobileNavLink to="/futures/BTCUSDT" onClick={() => setMobileMenuOpen(false)}>
                    선물거래
                  </MobileNavLink>
                  <MobileNavLink to="/portfolio" onClick={() => setMobileMenuOpen(false)}>
                    현물 포트폴리오
                  </MobileNavLink>
                  <MobileNavLink to="/futures/portfolio" onClick={() => setMobileMenuOpen(false)}>
                    선물 포트폴리오
                  </MobileNavLink>
                </>
              )}
              
              <div className="pt-4 border-t border-gray-700">
                {isAuthenticated ? (
                  <>
                    <p className="px-4 py-2 text-gray-400">
                      <span className="text-white font-semibold">{user?.username}</span>님
                    </p>
                    <button
                      onClick={handleLogout}
                      className="w-full text-left px-4 py-2 hover:bg-gray-700 rounded-lg transition-colors text-red-400"
                    >
                      로그아웃
                    </button>
                  </>
                ) : (
                  <>
                    <MobileNavLink to="/login" onClick={() => setMobileMenuOpen(false)}>
                      로그인
                    </MobileNavLink>
                    <MobileNavLink to="/register" onClick={() => setMobileMenuOpen(false)}>
                      회원가입
                    </MobileNavLink>
                  </>
                )}
              </div>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
};

// 네비게이션 링크 컴포넌트
const NavLink = ({ to, active, exact, children }) => (
  <Link
    to={to}
    className={`px-4 py-2 rounded-lg transition-colors ${
      active
        ? 'bg-gray-700 text-accent'
        : 'text-gray-300 hover:text-white hover:bg-gray-700'
    }`}
  >
    {children}
  </Link>
);

// 모바일 네비게이션 링크 컴포넌트
const MobileNavLink = ({ to, onClick, children }) => (
  <Link
    to={to}
    onClick={onClick}
    className="px-4 py-2 hover:bg-gray-700 rounded-lg transition-colors"
  >
    {children}
  </Link>
);

export default Header;