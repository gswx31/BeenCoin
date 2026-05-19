import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import Navbar from './Navbar';

const Layout = () => {
  const access = localStorage.getItem('token');
  const refresh = localStorage.getItem('refresh_token');
  // access나 refresh 중 하나라도 있으면 통과 (interceptor가 자동 갱신)
  if (!access && !refresh) return <Navigate to="/login" />;

  return (
    <>
      <Navbar />
      <main>
        <Outlet />
      </main>
    </>
  );
};

export default Layout;
