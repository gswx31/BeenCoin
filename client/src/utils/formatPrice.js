// client/src/utils/formatPrice.js
// =============================================================================
// 가격 포맷팅 유틸리티
// =============================================================================

/**
 * 가격을 포맷팅합니다.
 * @param {number|string} price - 포맷할 가격
 * @param {number} decimals - 소수점 자릿수 (기본: 자동)
 * @returns {string} 포맷된 가격 문자열
 */
export const formatPrice = (price, decimals = null) => {
  if (price === null || price === undefined || isNaN(price)) {
    return '0.00';
  }

  const numPrice = typeof price === 'string' ? parseFloat(price) : price;

  if (isNaN(numPrice)) {
    return '0.00';
  }

  // 자동 소수점 결정
  if (decimals === null) {
    if (numPrice >= 10000) {
      decimals = 2;
    } else if (numPrice >= 100) {
      decimals = 2;
    } else if (numPrice >= 1) {
      decimals = 4;
    } else {
      decimals = 6;
    }
  }

  return numPrice.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

/**
 * 큰 숫자를 축약합니다. (1K, 1M, 1B)
 * @param {number} num - 축약할 숫자
 * @returns {string} 축약된 문자열
 */
export const formatLargeNumber = (num) => {
  if (num === null || num === undefined) return '0';
  
  const absNum = Math.abs(num);
  const sign = num < 0 ? '-' : '';

  if (absNum >= 1e9) {
    return sign + (absNum / 1e9).toFixed(2) + 'B';
  }
  if (absNum >= 1e6) {
    return sign + (absNum / 1e6).toFixed(2) + 'M';
  }
  if (absNum >= 1e3) {
    return sign + (absNum / 1e3).toFixed(2) + 'K';
  }
  return sign + absNum.toFixed(2);
};

/**
 * 퍼센트를 포맷팅합니다.
 * @param {number} value - 퍼센트 값
 * @param {boolean} showSign - 부호 표시 여부
 * @returns {string} 포맷된 퍼센트 문자열
 */
export const formatPercent = (value, showSign = true) => {
  if (value === null || value === undefined || isNaN(value)) {
    return '0.00%';
  }

  const sign = showSign && value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};

export default formatPrice;