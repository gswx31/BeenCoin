# test_binance_api.py
"""
Binance API 연결 테스트 스크립트
실행: python test_binance_api.py
"""
import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.binance_service import (
    test_connection,
    get_current_price,
    get_multiple_prices,
    get_coin_info,
    get_24h_ticker,
    get_server_time
)


async def test_all():
    """모든 Binance API 기능 테스트"""
    
    print("=" * 60)
    print("🧪 Binance API 연결 테스트")
    print("=" * 60)
    print()
    
    # 1. 연결 테스트
    print("1️⃣ 연결 테스트")
    print("-" * 60)
    is_connected = await test_connection()
    if is_connected:
        print("✅ Binance API 연결 성공")
    else:
        print("❌ Binance API 연결 실패")
        return
    print()
    
    # 2. 서버 시간
    print("2️⃣ 서버 시간 조회")
    print("-" * 60)
    server_time = await get_server_time()
    print(f"서버 타임스탬프: {server_time}")
    from datetime import datetime
    if server_time > 0:
        dt = datetime.fromtimestamp(server_time / 1000)
        print(f"서버 시간: {dt}")
    print()
    
    # 3. 단일 코인 가격 조회
    print("3️⃣ 단일 코인 가격 조회")
    print("-" * 60)
    test_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    
    for symbol in test_symbols:
        try:
            price = await get_current_price(symbol)
            print(f"✅ {symbol}: ${price:,.2f}")
        except Exception as e:
            print(f"❌ {symbol}: {str(e)}")
    print()
    
    # 4. 다중 코인 가격 조회
    print("4️⃣ 다중 코인 가격 조회")
    print("-" * 60)
    prices = await get_multiple_prices(test_symbols)
    for symbol, price in prices.items():
        print(f"✅ {symbol}: ${price:,.2f}")
    print()
    
    # 5. 24h 티커 정보
    print("5️⃣ 24시간 티커 정보")
    print("-" * 60)
    ticker = await get_24h_ticker("BTCUSDT")
    if ticker:
        print(f"심볼: {ticker.get('symbol')}")
        print(f"현재가: ${float(ticker.get('lastPrice', 0)):,.2f}")
        print(f"24h 변동: {float(ticker.get('priceChangePercent', 0)):.2f}%")
        print(f"24h 거래량: {float(ticker.get('volume', 0)):,.2f}")
        print(f"24h 최고가: ${float(ticker.get('highPrice', 0)):,.2f}")
        print(f"24h 최저가: ${float(ticker.get('lowPrice', 0)):,.2f}")
    else:
        print("❌ 티커 정보 조회 실패")
    print()
    
    # 6. 코인 상세 정보
    print("6️⃣ 코인 상세 정보")
    print("-" * 60)
    try:
        info = await get_coin_info("BTCUSDT")
        print(f"심볼: {info['symbol']}")
        print(f"가격: ${float(info['price']):,.2f}")
        print(f"변동률: {float(info['change']):.2f}%")
        print(f"거래량: {float(info['volume']):,.2f}")
    except Exception as e:
        print(f"❌ 코인 정보 조회 실패: {e}")
    print()
    
    # 7. 유효하지 않은 심볼 테스트
    print("7️⃣ 잘못된 심볼 처리 테스트")
    print("-" * 60)
    try:
        price = await get_current_price("INVALIDUSDT")
        print(f"예상치 못한 성공: {price}")
    except Exception as e:
        print(f"✅ 예상대로 에러 발생: {str(e)[:100]}")
    print()
    
    print("=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    # asyncio 실행
    asyncio.run(test_all())