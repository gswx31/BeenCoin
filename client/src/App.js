// client/src/App.js
// =============================================================================
// 메인 앱 컴포넌트 - 선물 거래 전용
// =============================================================================
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

// Contexts
import { AuthProvider } from './contexts/AuthContext';
import { MarketProvider } from './contexts/MarketContext';
import { FuturesProvider } from './contexts/FuturesContext';

// Layout
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';

// Pages
import Dashboard from './components/dashboard/Dashboard';
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import FuturesTrading from './components/trading/FuturesTrading';
import FuturesPortfolio from './components/portfolio/FuturesPortfolio';

// Protected Route
import ProtectedRoute from './components/common/ProtectedRoute';

function App() {
  return (
    <AuthProvider>
      <MarketProvider>
        <FuturesProvider>
          <Router>
            <div className="min-h-screen bg-gray-900 text-white flex flex-col">
              <Header />
              
              <main className="flex-grow container mx-auto px-4 py-8">
                <Routes>
                  {/* 공개 페이지 */}
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />

                  {/* 선물 거래 (인증 필요) */}
                  <Route
                    path="/futures/:symbol"
                    element={
                      <ProtectedRoute>
                        <FuturesTrading />
                      </ProtectedRoute>
                    }
                  />

                  {/* 선물 포트폴리오 (인증 필요) */}
                  <Route
                    path="/futures/portfolio"
                    element={
                      <ProtectedRoute>
                        <FuturesPortfolio />
                      </ProtectedRoute>
                    }
                  />

                  {/* 기존 라우트 리다이렉트 */}
                  <Route path="/trading" element={<Navigate to="/futures/BTCUSDT" replace />} />
                  <Route path="/trading/:symbol" element={<Navigate to="/futures/BTCUSDT" replace />} />
                  <Route path="/portfolio" element={<Navigate to="/futures/portfolio" replace />} />
                  <Route path="/trade/:symbol" element={<Navigate to="/futures/BTCUSDT" replace />} />

                  {/* 404 */}
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </main>

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
              />
            </div>
          </Router>
        </FuturesProvider>
      </MarketProvider>
    </AuthProvider>
  );
}

export default App;