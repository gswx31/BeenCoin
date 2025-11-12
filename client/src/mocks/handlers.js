import { rest } from 'msw';

export const handlers = [
  // Login
  rest.post('/api/v1/auth/login', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        access_token: 'fake-token',
        token_type: 'bearer'
      })
    );
  }),

  // Account info
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

  // Market data
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
          icon: '??,
          color: '#F7931A'
        }
      ])
    );
  }),

  // Create order
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
