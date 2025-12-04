// client/src/components/layout/Footer.js
// =============================================================================
// 푸터 컴포넌트
// =============================================================================
import React from 'react';

const Footer = () => {
  return (
    <footer className="bg-gray-800 border-t border-gray-700 py-6">
      <div className="container mx-auto px-4">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <div className="text-gray-400 text-sm mb-4 md:mb-0">
            © 2024 BeenCoin. 선물거래 시뮬레이션 플랫폼
          </div>
          <div className="flex items-center space-x-4 text-sm text-gray-400">
            <span className="flex items-center">
              <span className="w-2 h-2 bg-purple-500 rounded-full mr-2"></span>
              선물거래 전용
            </span>
            <span>|</span>
            <span>실시간 바이낸스 데이터</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;