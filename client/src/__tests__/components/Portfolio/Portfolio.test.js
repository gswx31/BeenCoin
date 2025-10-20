import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Portfolio from '../../../components/portfolio/Portfolio';
import { AuthProvider } from '../../../contexts/AuthContext';

const MockPortfolio = () => (
  <BrowserRouter>
    <AuthProvider>
      <Portfolio />
    </AuthProvider>
  </BrowserRouter>
);

describe('Portfolio Component', () => {
  test('loads portfolio data', async () => {
    render(<MockPortfolio />);

    await waitFor(() => {
      expect(screen.getByText(/total assets/i)).toBeInTheDocument();
      expect(screen.getByText(/1,000,000/)).toBeInTheDocument();
    });
  });

  test('displays positions list', async () => {
    render(<MockPortfolio />);

    await waitFor(() => {
      expect(screen.getByText(/BTCUSDT/i)).toBeInTheDocument();
      expect(screen.getByText(/0.5/)).toBeInTheDocument();
    });
  });

  test('calculates profit rate correctly', async () => {
    render(<MockPortfolio />);

    await waitFor(() => {
      expect(screen.getByText(/10.0%/)).toBeInTheDocument();
    });
  });
});
