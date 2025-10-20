# 프로젝트 루트 디렉토리에서 실행

# 1. 테스트 설정 파일 생성
mkdir -p client/src/mocks
cat > client/src/setupTests.js << 'EOF'
import '@testing-library/jest-dom';
import { server } from './mocks/server';

// MSW 서버 설정
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
EOF

# 2. MSW 핸들러 생성
cat > client/src/mocks/handlers.js << 'EOF'
import { rest } from 'msw';

export const handlers = [
  // 로그인
  rest.post('/api/v1/auth/login', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        access_token: 'fake-token',
        token_type: 'bearer'
      })
    );
  }),

  // 계정 정보
  rest.get('/api/v1/account/', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        id: 1,
        user_id: 1,
        usdt_balance: 1000000,
        total_profit: 50000,
        profit_rate: 5.0,
        positions: [
          {
            symbol: 'BTCUSDT',
            quantity: 0.5,
            average_price: 50000,
            current_price: 55000,
            current_value: 27500,
            unrealized_profit: 2500,
            profit_rate: 10.0
          }
        ]
      })
    );
  }),

  // 시장 데이터
  rest.get('/api/v1/market/coins', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json([
        {
          symbol: 'BTCUSDT',
          name: 'Bitcoin',
          price: 50000,
          change: 5.2,
          volume: 1000000000,
          icon: '₿',
          color: '#F7931A'
        }
      ])
    );
  }),

  // 주문 생성
  rest.post('/api/v1/orders/', (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        id: 1,
        symbol: 'BTCUSDT',
        side: 'BUY',
        order_type: 'MARKET',
        status: 'FILLED',
        quantity: 0.001,
        average_price: 50000
      })
    );
  })
];
EOF

# 3. MSW 서버 설정
cat > client/src/mocks/server.js << 'EOF'
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
EOF

# 4. 테스트 디렉토리 생성 및 테스트 파일들 생성
mkdir -p client/src/__tests__/components/Auth
mkdir -p client/src/__tests__/components/Portfolio
mkdir -p client/src/__tests__/components/Trading
mkdir -p client/src/__tests__/utils
mkdir -p client/src/__tests__/contexts

# 5. Login 컴포넌트 테스트
cat > client/src/__tests__/components/Auth/Login.test.js << 'EOF'
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Login from '../../../components/auth/Login';
import { AuthProvider } from '../../../contexts/AuthContext';

const MockLogin = () => (
  <BrowserRouter>
    <AuthProvider>
      <Login />
    </AuthProvider>
  </BrowserRouter>
);

describe('Login Component', () => {
  test('로그인 폼이 렌더링된다', () => {
    render(<MockLogin />);
    
    expect(screen.getByLabelText(/아이디/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/비밀번호/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /로그인/i })).toBeInTheDocument();
  });

  test('입력값이 변경된다', () => {
    render(<MockLogin />);
    
    const usernameInput = screen.getByLabelText(/아이디/i);
    const passwordInput = screen.getByLabelText(/비밀번호/i);

    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'testpass123' } });

    expect(usernameInput.value).toBe('testuser');
    expect(passwordInput.value).toBe('testpass123');
  });

  test('로그인이 성공한다', async () => {
    render(<MockLogin />);
    
    const usernameInput = screen.getByLabelText(/아이디/i);
    const passwordInput = screen.getByLabelText(/비밀번호/i);
    const submitButton = screen.getByRole('button', { name: /로그인/i });

    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'testpass123' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(localStorage.getItem('token')).toBeTruthy();
    });
  });

  test('빈 값으로 제출 시 에러가 표시된다', async () => {
    render(<MockLogin />);
    
    const submitButton = screen.getByRole('button', { name: /로그인/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/아이디를 입력하세요/i)).toBeInTheDocument();
    });
  });
});
EOF

# 6. Portfolio 컴포넌트 테스트
cat > client/src/__tests__/components/Portfolio/Portfolio.test.js << 'EOF'
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
  test('포트폴리오 데이터가 로드된다', async () => {
    render(<MockPortfolio />);

    await waitFor(() => {
      expect(screen.getByText(/총 자산/i)).toBeInTheDocument();
      expect(screen.getByText(/1,000,000/)).toBeInTheDocument();
    });
  });

  test('포지션 목록이 표시된다', async () => {
    render(<MockPortfolio />);

    await waitFor(() => {
      expect(screen.getByText(/BTCUSDT/i)).toBeInTheDocument();
      expect(screen.getByText(/0.5/)).toBeInTheDocument();
    });
  });

  test('수익률이 올바르게 계산된다', async () => {
    render(<MockPortfolio />);

    await waitFor(() => {
      expect(screen.getByText(/10.0%/)).toBeInTheDocument();
    });
  });
});
EOF

# 7. OrderForm 컴포넌트 테스트
cat > client/src/__tests__/components/Trading/OrderForm.test.js << 'EOF'
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import OrderForm from '../../../components/trading/OrderForm';
import { AuthProvider } from '../../../contexts/AuthContext';

const MockOrderForm = () => (
  <BrowserRouter>
    <AuthProvider>
      <OrderForm symbol="BTCUSDT" currentPrice={50000} />
    </AuthProvider>
  </BrowserRouter>
);

describe('OrderForm Component', () => {
  test('주문 폼이 렌더링된다', () => {
    render(<MockOrderForm />);
    
    expect(screen.getByText(/매수/i)).toBeInTheDocument();
    expect(screen.getByText(/매도/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/수량/i)).toBeInTheDocument();
  });

  test('매수/매도 탭을 전환할 수 있다', () => {
    render(<MockOrderForm />);
    
    const sellTab = screen.getByText(/매도/i);
    fireEvent.click(sellTab);
    
    expect(screen.getByRole('button', { name: /매도하기/i })).toBeInTheDocument();
  });

  test('수량 입력이 작동한다', () => {
    render(<MockOrderForm />);
    
    const quantityInput = screen.getByPlaceholderText(/수량/i);
    fireEvent.change(quantityInput, { target: { value: '0.001' } });
    
    expect(quantityInput.value).toBe('0.001');
  });

  test('퍼센트 버튼이 작동한다', () => {
    render(<MockOrderForm />);
    
    const percent25Button = screen.getByText('25%');
    fireEvent.click(percent25Button);
    
    // 25% 버튼이 활성화되었는지 확인
    expect(percent25Button).toHaveClass('bg-accent');
  });

  test('주문 제출이 성공한다', async () => {
    render(<MockOrderForm />);
    
    const quantityInput = screen.getByPlaceholderText(/수량/i);
    const submitButton = screen.getByRole('button', { name: /매수하기/i });

    fireEvent.change(quantityInput, { target: { value: '0.001' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/체결 완료/i)).toBeInTheDocument();
    });
  });
});
EOF

# 8. 유틸리티 함수 테스트
cat > client/src/__tests__/utils/formatPrice.test.js << 'EOF'
import { formatPrice } from '../../../utils/formatPrice';

describe('formatPrice', () => {
  test('큰 가격을 올바르게 포맷한다', () => {
    expect(formatPrice(100000)).toBe('100,000');
    expect(formatPrice(50000)).toBe('50,000');
  });

  test('중간 가격을 올바르게 포맷한다', () => {
    expect(formatPrice(5000.12)).toBe('5,000.12');
    expect(formatPrice(100.50)).toBe('100.50');
  });

  test('작은 가격을 올바르게 포맷한다', () => {
    expect(formatPrice(0.6612)).toBe('0.6612');
    expect(formatPrice(0.01234)).toBe('0.0123');
  });

  test('매우 작은 가격을 올바르게 포맷한다', () => {
    expect(formatPrice(0.00012345)).toBe('0.000123');
  });

  test('0을 올바르게 처리한다', () => {
    expect(formatPrice(0)).toBe('0');
    expect(formatPrice(null)).toBe('0');
  });
});
EOF

# 9. AuthContext 테스트
cat > client/src/__tests__/contexts/AuthContext.test.js << 'EOF'
import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../../../contexts/AuthContext';

describe('AuthContext', () => {
  test('초기 상태는 로그아웃 상태다', () => {
    const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;
    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
  });

  test('로그인이 성공하면 상태가 업데이트된다', async () => {
    const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;
    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.login('testuser', 'testpass123');
    });

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true);
      expect(localStorage.getItem('token')).toBeTruthy();
    });
  });

  test('로그아웃이 상태를 초기화한다', async () => {
    const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;
    const { result } = renderHook(() => useAuth(), { wrapper });

    // 먼저 로그인
    await act(async () => {
      await result.current.login('testuser', 'testpass123');
    });

    // 그 다음 로그아웃
    act(() => {
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(localStorage.getItem('token')).toBeNull();
  });
});
EOF

echo "✅ 모든 테스트 파일이 생성되었습니다!"