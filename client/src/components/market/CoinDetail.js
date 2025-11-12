// client/src/components/market/CoinDetail.js
import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

const CoinDetail = () => {
  const { symbol } = useParams();
  const navigate = useNavigate();

  // 모의투자이므로 바로 거래 화면으로 리다이렉트
  useEffect(() => {
    navigate(`/trade/${symbol}`, { replace: true });
  }, [symbol, navigate]);

  return null; // 실제로는 이 컴포넌트가 렌더링되지 않음
};

export default CoinDetail;