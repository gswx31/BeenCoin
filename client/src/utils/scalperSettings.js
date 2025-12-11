// client/src/utils/scalperSettings.js
// =============================================================================
// 단타 모드 설정 저장/불러오기 (LocalStorage)
// =============================================================================

const STORAGE_KEY = 'beencoin_scalper_settings';

export const defaultScalperSettings = {
  enabled: false,
  stopLossPercent: 3,
  takeProfitPercent: 6,
};

// 설정 저장
export const saveScalperSettings = (settings) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    return true;
  } catch (error) {
    console.error('단타 설정 저장 실패:', error);
    return false;
  }
};

// 설정 불러오기
export const loadScalperSettings = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      return JSON.parse(saved);
    }
    return defaultScalperSettings;
  } catch (error) {
    console.error('단타 설정 불러오기 실패:', error);
    return defaultScalperSettings;
  }
};

// 설정 초기화
export const resetScalperSettings = () => {
  try {
    localStorage.removeItem(STORAGE_KEY);
    return true;
  } catch (error) {
    console.error('단타 설정 초기화 실패:', error);
    return false;
  }
};