// client/src/App.js - 개선된 버전
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { MarketProvider } from './contexts/MarketContext';
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import Dashboard from './components/dashboard/Dashboard';
import CoinDetail from './components/market/CoinDetail';
import Trading from './components/trading/Trading';
import Portfolio from './components/portfolio/Portfolio';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import './index.css';

function App() {
  return (
    <AuthProvider>
      <MarketProvider>
        <Router>
          <div className="min-h-screen bg-gray-900 text-white">
            <Header />
            <main className="container mx-auto px-4 py-6">
              <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/" element={<Dashboard />} />
                <Route path="/coin/:symbol" element={<CoinDetail />} />
                <Route path="/trade/:symbol" element={<Trading />} />
                <Route path="/portfolio" element={<Portfolio />} />
              </Routes>
            </main>
            <Footer />
            <ToastContainer 
              position="bottom-right"
              autoClose={3000}
              theme="dark"
            />
          </div>
        </Router>
      </MarketProvider>
    </AuthProvider>
  );
}

export default App;