from binance.client import Client
from app.core.config import settings
import asyncio
from binance import AsyncClient, BinanceSocketManager

async_client = AsyncClient(settings.BINANCE_API_KEY, settings.BINANCE_API_SECRET)

async def get_current_price(symbol: str) -> float:
    ticker = await async_client.get_symbol_ticker(symbol=symbol)
    return float(ticker['price'])

async def monitor_limit_order(order_id: int, symbol: str, side: str, price: float, quantity: float, callback):
    async with BinanceSocketManager(async_client) as bsm:
        ts = bsm.trade_socket(symbol)
        async with ts as tscm:
            while True:
                res = await tscm.recv()
                current_price = float(res['p'])
                if (side == 'buy' and current_price <= price) or (side == 'sell' and current_price >= price):
                    await callback(order_id, quantity, current_price)
                    break

def execute_market_order(symbol: str, side: str, quantity: float):
    price = client.get_symbol_ticker(symbol=symbol)['price']
    return float(price)
