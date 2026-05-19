import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import CheckInModal from './CheckInModal';
import WelcomeGuide from './WelcomeGuide';

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
      <WelcomeGuide />
    </>
  );
};

export default Layout;
