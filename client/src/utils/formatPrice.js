// client/src/utils/formatPrice.js
export const formatPrice = (price) => {
  if (!price || price === 0) return '0';
  
  const priceNum = parseFloat(price);
  
  // 가격 크기에 따라 소수점 자릿수 결정
  if (priceNum >= 10000) {
    // $10,000 이상: 소수점 없이
    return priceNum.toLocaleString('ko-KR', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    });
  } else if (priceNum >= 1000) {
    // $1,000 ~ $9,999: 소수점 2자리
    return priceNum.toLocaleString('ko-KR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  } else if (priceNum >= 100) {
    // $100 ~ $999: 소수점 2자리
    return priceNum.toLocaleString('ko-KR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  } else if (priceNum >= 1) {
    // $1 ~ $99: 소수점 3자리
    return priceNum.toLocaleString('ko-KR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 3
    });
  } else if (priceNum >= 0.01) {
    // $0.01 ~ $0.99: 소수점 4자리
    return priceNum.toLocaleString('ko-KR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 4
    });
  } else if (priceNum >= 0.0001) {
    // $0.0001 ~ $0.0099: 소수점 6자리
    return priceNum.toLocaleString('ko-KR', {
      minimumFractionDigits: 4,
      maximumFractionDigits: 6
    });
  } else {
    // $0.0001 미만: 소수점 8자리
    return priceNum.toLocaleString('ko-KR', {
      minimumFractionDigits: 6,
      maximumFractionDigits: 8
    });
  }
};