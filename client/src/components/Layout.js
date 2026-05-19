import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import CheckInModal from './CheckInModal';

const Layout = () => {
  const access = localStorage.getItem('token');
  const refresh = localStorage.getItem('refresh_token');
  if (!access && !refresh) return <Navigate to="/login" />;

  return (
    <>
      <Navbar />
      <main>
        <Outlet />
      </main>
      <CheckInModal />
    </>
  );
};

export default Layout;
