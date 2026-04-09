import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

const navItems = [
  { path: '/dashboard', label: '홈' },
  { path: '/order', label: '거래' },
  { path: '/portfolio', label: '내 자산' },
  { path: '/analytics', label: '분석' },
  { path: '/leaderboard', label: '랭킹' },
  { path: '/achievements', label: '업적' },
  { path: '/history', label: '내역' },
];

const Navbar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav className="bg-dark-800 border-b border-dark-600 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          <div className="flex items-center space-x-6">
            <Link to="/dashboard" className="flex items-center space-x-2">
              <span className="text-xl">🪙</span>
              <span className="text-accent font-bold text-lg hidden sm:block">빈코인</span>
            </Link>

            <div className="hidden lg:flex space-x-1">
              {navItems.map((item) => (
                <Link key={item.path} to={item.path}
                  className={`px-3 py-1.5 rounded-xl text-sm font-medium transition-all ${
                    location.pathname === item.path
                      ? 'text-accent bg-accent-soft'
                      : 'text-muted hover:text-white hover:bg-dark-700'
                  }`}>
                  {item.label}
                </Link>
              ))}
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <span className="hidden sm:inline-flex items-center px-3 py-1 rounded-full text-[10px] font-semibold bg-mint/10 text-mint border border-mint/20">
              모의투자
            </span>
            <button onClick={() => { localStorage.removeItem('token'); navigate('/login'); }}
              className="text-muted hover:text-loss text-sm transition-colors hidden lg:block">
              로그아웃
            </button>
            <button onClick={() => setMobileOpen(!mobileOpen)} className="lg:hidden text-muted hover:text-white p-1">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {mobileOpen
                  ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
              </svg>
            </button>
          </div>
        </div>
      </div>

      {mobileOpen && (
        <div className="lg:hidden border-t border-dark-600 bg-dark-800 fade-in">
          <div className="px-4 py-3 space-y-1">
            {navItems.map((item) => (
              <Link key={item.path} to={item.path} onClick={() => setMobileOpen(false)}
                className={`block px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  location.pathname === item.path ? 'bg-dark-700 text-accent' : 'text-muted hover:text-white hover:bg-dark-700'
                }`}>{item.label}</Link>
            ))}
            <button onClick={() => { localStorage.removeItem('token'); navigate('/login'); }}
              className="block w-full text-left px-3 py-2.5 rounded-xl text-sm font-medium text-loss hover:bg-dark-700">로그아웃</button>
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
