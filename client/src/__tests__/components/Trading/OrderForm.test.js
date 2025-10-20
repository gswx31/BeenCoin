import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import OrderForm from '../../../components/trading/OrderForm';
import { AuthProvider } from '../../../contexts/AuthContext';

const MockOrderForm = () => (
  <BrowserRouter>
    <AuthProvider>
      <OrderForm symbol='BTCUSDT' currentPrice={50000} />
    </AuthProvider>
  </BrowserRouter>
);

describe('OrderForm Component', () => {
  test('renders order form', () => {
    render(<MockOrderForm />);
    
    expect(screen.getByText(/buy/i)).toBeInTheDocument();
    expect(screen.getByText(/sell/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/quantity/i)).toBeInTheDocument();
  });

  test('switches between buy/sell tabs', () => {
    render(<MockOrderForm />);
    
    const sellTab = screen.getByText(/sell/i);
    fireEvent.click(sellTab);
    
    expect(screen.getByRole('button', { name: /sell/i })).toBeInTheDocument();
  });

  test('handles quantity input', () => {
    render(<MockOrderForm />);
    
    const quantityInput = screen.getByPlaceholderText(/quantity/i);
    fireEvent.change(quantityInput, { target: { value: '0.001' } });
    
    expect(quantityInput.value).toBe('0.001');
  });

  test('percentage buttons work', () => {
    render(<MockOrderForm />);
    
    const percent25Button = screen.getByText('25%');
    fireEvent.click(percent25Button);
    
    // Check if 25% button is activated
    expect(percent25Button).toHaveClass('bg-accent');
  });

  test('submits order successfully', async () => {
    render(<MockOrderForm />);
    
    const quantityInput = screen.getByPlaceholderText(/quantity/i);
    const submitButton = screen.getByRole('button', { name: /buy/i });

    fireEvent.change(quantityInput, { target: { value: '0.001' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/order filled/i)).toBeInTheDocument();
    });
  });
});
