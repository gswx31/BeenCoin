// client/src/App.js
// =============================================================================
// BeenCoin 메인 앱 - 라우팅 및 Context 통합
// =============================================================================
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

// Context Providers
import { AuthProvider } from './contexts/AuthContext';
import { MarketProvider } from './contexts/MarketContext';
import { FuturesProvider } from './contexts/FuturesContext';

// Layout Components
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';

// Auth Components
import Login from './components/auth/Login';
import Register from './components/auth/Register';

// Dashboard & Market
import Dashboard from './components/dashboard/Dashboard';

// Trading Components
import FuturesTrading from './components/trading/FuturesTrading';
import Trading from './components/trading/Trading'; // 현물 거래 (기존)

// Portfolio Components
import Portfolio from './components/portfolio/Portfolio'; // 현물 포트폴리오
import FuturesPortfolio from './components/portfolio/FuturesPortfolio'; // 선물 포트폴리오

// Protected Route Component
import ProtectedRoute from './components/common/ProtectedRoute';

// Styles
import './index.css';

function App() {
  return (
    <Router>
      <AuthProvider>
        <MarketProvider>
          <FuturesProvider>
            <div className="min-h-screen bg-gray-900 text-white flex flex-col">
              {/* 헤더 */}
              <Header />

              {/* 메인 컨텐츠 */}
              <main className="flex-1 container mx-auto px-4 py-6">
                <Routes>
                  {/* 공개 라우트 */}
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />
                  
                  {/* 대시보드 (기본 페이지) */}
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/dashboard" element={<Dashboard />} />

                  {/* 현물 거래 (기존) */}
                  <Route
                    path="/trade/:symbol"
                    element={
                      <ProtectedRoute>
                        <Trading />
                      </ProtectedRoute>
                    }
                  />

                  {/* 선물 거래 (신규) */}
                  <Route
                    path="/futures/:symbol"
                    element={
                      <ProtectedRoute>
                        <FuturesTrading />
                      </ProtectedRoute>
                    }
                  />

                  {/* 현물 포트폴리오 */}
                  <Route
                    path="/portfolio"
                    element={
                      <ProtectedRoute>
                        <Portfolio />
                      </ProtectedRoute>
                    }
                  />

                  {/* 선물 포트폴리오 */}
                  <Route
                    path="/futures/portfolio"
                    element={
                      <ProtectedRoute>
                        <FuturesPortfolio />
                      </ProtectedRoute>
                    }
                  />

                  {/* 404 - 존재하지 않는 페이지 */}
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </main>

              {/* 푸터 */}
              <Footer />

              {/* Toast 알림 */}
              <ToastContainer
                position="top-right"
                autoClose={3000}
                hideProgressBar={false}
                newestOnTop
                closeOnClick
                rtl={false}
                pauseOnFocusLoss
                draggable
                pauseOnHover
                theme="dark"
                limit={5}
              />
            </div>
          </FuturesProvider>
        </MarketProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;