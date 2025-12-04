// client/src/components/common/ProtectedRoute.js
// =============================================================================
// 인증 필요 라우트 래퍼
// =============================================================================
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  // 로딩 중
  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-teal-500"></div>
      </div>
    );
  }

  // 비인증 사용자
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};

export default ProtectedRoute;