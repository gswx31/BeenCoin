// client/src/utils/tradeNotifications.js
// =============================================================================
// 거래 알림 효과 유틸리티
// - 체결 토스트 알림
// - 사운드 효과
// - 화면 플래시 효과
// =============================================================================
import { toast } from 'react-toastify';

/**
 * 포지션 오픈 알림
 */
export const notifyPositionOpened = (position) => {
  const isLong = position.side === 'LONG';
  
  toast.success(
    <div className="flex items-center space-x-3">
      <div className={`text-2xl ${isLong ? 'text-green-400' : 'text-red-400'}`}>
        {isLong ? '📈' : '📉'}
      </div>
      <div>
        <div className="font-bold">
          {isLong ? 'LONG' : 'SHORT'} 포지션 진입
        </div>
        <div className="text-sm text-gray-300">
          {position.symbol} {position.leverage}x | 
          ${parseFloat(position.entry_price).toLocaleString()}
        </div>
      </div>
    </div>,
    {
      position: 'top-right',
      autoClose: 3000,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
      draggable: true,
      className: isLong ? 'bg-green-900/90' : 'bg-red-900/90',
    }
  );

  // 사운드 효과
  playTradeSound(isLong ? 'open-long' : 'open-short');
};

/**
 * 포지션 청산 알림
 */
export const notifyPositionClosed = (position, pnl, roe) => {
  const isProfit = pnl >= 0;
  
  toast(
    <div className="flex items-center space-x-3">
      <div className={`text-2xl ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
        {isProfit ? '💰' : '📊'}
      </div>
      <div>
        <div className="font-bold">
          포지션 청산 완료
        </div>
        <div className="text-sm text-gray-300">
          {position.symbol} | 
          손익: {isProfit ? '+' : ''}${pnl.toFixed(2)} 
          ({isProfit ? '+' : ''}{roe.toFixed(2)}%)
        </div>
      </div>
    </div>,
    {
      type: isProfit ? 'success' : 'warning',
      position: 'top-right',
      autoClose: 4000,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
      draggable: true,
      className: isProfit ? 'bg-green-900/90' : 'bg-red-900/90',
    }
  );

  // 사운드 효과
  playTradeSound(isProfit ? 'profit' : 'loss');
};

/**
 * 지정가 체결 알림
 */
export const notifyLimitOrderFilled = (order) => {
  toast.info(
    <div className="flex items-center space-x-3">
      <div className="text-2xl">📝</div>
      <div>
        <div className="font-bold">지정가 주문 체결</div>
        <div className="text-sm text-gray-300">
          {order.symbol} {order.side} | ${parseFloat(order.price).toLocaleString()}
        </div>
      </div>
    </div>,
    {
      position: 'top-right',
      autoClose: 3000,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
      draggable: true,
    }
  );

  playTradeSound('limit-filled');
};

/**
 * 강제 청산 알림
 */
export const notifyLiquidation = (position) => {
  toast.error(
    <div className="flex items-center space-x-3">
      <div className="text-2xl">⚠️</div>
      <div>
        <div className="font-bold text-red-400">강제 청산 발생!</div>
        <div className="text-sm text-gray-300">
          {position.symbol} | 청산가: ${parseFloat(position.liquidation_price).toLocaleString()}
        </div>
      </div>
    </div>,
    {
      position: 'top-center',
      autoClose: 5000,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
      draggable: false,
      className: 'bg-red-900',
    }
  );

  playTradeSound('liquidation');
  flashScreen('red', 300);
};

/**
 * 거래 사운드 재생
 */
export const playTradeSound = (type) => {
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    // 사운드 타입별 주파수 설정
    const soundSettings = {
      'open-long': { freq: 880, duration: 0.15 },     // 롱 진입: 높은 음
      'open-short': { freq: 440, duration: 0.15 },    // 숏 진입: 낮은 음
      'profit': { freq: 1000, duration: 0.2 },        // 수익: 매우 높은 음
      'loss': { freq: 300, duration: 0.2 },           // 손실: 낮은 음
      'limit-filled': { freq: 660, duration: 0.1 },   // 지정가 체결: 중간 음
      'liquidation': { freq: 200, duration: 0.3 },    // 청산: 매우 낮은 음
    };
    
    const setting = soundSettings[type] || soundSettings['open-long'];
    
    oscillator.frequency.value = setting.freq;
    oscillator.type = 'sine';
    
    gainNode.gain.setValueAtTime(0.05, audioContext.currentTime); // 볼륨 낮춤
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + setting.duration);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + setting.duration);
  } catch (error) {
    console.warn('사운드 재생 실패:', error);
  }
};

/**
 * 화면 플래시 효과
 */
export const flashScreen = (color = 'green', duration = 200) => {
  try {
    const flashOverlay = document.createElement('div');
    flashOverlay.className = 'fixed inset-0 pointer-events-none z-50 transition-opacity';
    flashOverlay.style.opacity = '0';
    
    // 색상 설정
    const colors = {
      green: 'rgba(16, 185, 129, 0.15)',
      red: 'rgba(239, 68, 68, 0.15)',
      blue: 'rgba(59, 130, 246, 0.15)',
      yellow: 'rgba(234, 179, 8, 0.15)',
    };
    
    flashOverlay.style.backgroundColor = colors[color] || colors.green;
    
    document.body.appendChild(flashOverlay);
    
    // 페이드 인
    setTimeout(() => {
      flashOverlay.style.opacity = '1';
    }, 10);
    
    // 페이드 아웃 및 제거
    setTimeout(() => {
      flashOverlay.style.opacity = '0';
      setTimeout(() => {
        if (document.body.contains(flashOverlay)) {
          document.body.removeChild(flashOverlay);
        }
      }, 300);
    }, duration);
  } catch (error) {
    console.warn('플래시 효과 실패:', error);
  }
};

/**
 * 가격 변동 알림 (선택적)
 */
export const notifyPriceAlert = (symbol, targetPrice, currentPrice, direction) => {
  toast.warning(
    <div className="flex items-center space-x-3">
      <div className="text-2xl">🔔</div>
      <div>
        <div className="font-bold">가격 알림</div>
        <div className="text-sm text-gray-300">
          {symbol}이(가) ${targetPrice.toLocaleString()}에 도달했습니다!
        </div>
      </div>
    </div>,
    {
      position: 'top-right',
      autoClose: 5000,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
      draggable: true,
    }
  );

  playTradeSound('limit-filled');
};

export default {
  notifyPositionOpened,
  notifyPositionClosed,
  notifyLimitOrderFilled,
  notifyLiquidation,
  notifyPriceAlert,
  playTradeSound,
  flashScreen,
};