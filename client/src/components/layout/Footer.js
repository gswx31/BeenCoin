// client/src/components/layout/Footer.js
import React from 'react';

const Footer = () => {
  return (
    <footer className="bg-gray-800 border-t border-gray-700 mt-20">
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div>
            <h3 className="text-lg font-bold mb-4">BeenCoin</h3>
            <p className="text-gray-400 text-sm">
              실시간 암호화폐 모의투자 플랫폼
            </p>
          </div>
          <div>
            <h3 className="text-lg font-bold mb-4">서비스</h3>
            <ul className="space-y-2 text-sm text-gray-400">
              <li>실시간 시세</li>
              <li>모의투자</li>
              <li>포트폴리오 관리</li>
            </ul>
          </div>
          <div>
            <h3 className="text-lg font-bold mb-4">정보</h3>
            <p className="text-gray-400 text-sm">
              이 사이트는 교육 목적의 모의투자 플랫폼입니다.
              <br />
              실제 거래가 발생하지 않습니다.
            </p>
          </div>
        </div>
        <div className="border-t border-gray-700 mt-8 pt-8 text-center text-gray-400 text-sm">
          © 2025 BeenCoin. All rights reserved.
        </div>
      </div>
    </footer>
  );
};

export default Footer;