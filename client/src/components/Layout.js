import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import Navbar from './Navbar';

const Layout = () => {
  const token = localStorage.getItem('token');
  if (!token) return <Navigate to="/login" />;

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
