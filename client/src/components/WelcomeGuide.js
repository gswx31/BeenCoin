import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const STEPS = [
  {
    emoji: '👋',
    title: '환영해요!',
    desc: '진짜 돈이 아닌 가상 100만 달러로\n안전하게 코인 거래를 연습할 수 있어요.',
  },
  {
    emoji: '📈',
    title: '실시간 시세로 거래',
    desc: '바이낸스 거래소의 실제 가격을 그대로 사용해요.\n시장가/지정가 주문을 자유롭게 해보세요.',
  },
  {
    emoji: '🏆',
    title: '티어와 랭킹',
    desc: '거래를 잘하면 티어가 올라가요.\n다른 사용자와 수익률 경쟁도 가능해요!',
  },
  {
    emoji: '🎁',
    title: '매일 출석 보상',
    desc: '매일 접속해서 보너스를 받아보세요.\n7일 연속이면 럭키박스도 있어요!',
  },
  {
    emoji: '🚀',
    title: '준비 끝!',
    desc: '거래 페이지로 가서 첫 매수를 해볼까요?',
  },
];

const SEEN_KEY = 'welcome_guide_seen';

const WelcomeGuide = () => {
  const [show, setShow] = useState(false);
  const [step, setStep] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    if (!localStorage.getItem(SEEN_KEY)) {
      setShow(true);
    }
  }, []);

  const close = () => {
    localStorage.setItem(SEEN_KEY, '1');
    setShow(false);
  };

  const next = () => {
    if (step < STEPS.length - 1) setStep(step + 1);
    else { close(); navigate('/order'); }
  };

  if (!show) return null;
  const s = STEPS[step];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 fade-in">
      <div className="bg-dark-800 rounded-3xl border border-dark-600 p-8 max-w-md w-full">
        <div className="text-center mb-6">
          <div className="text-6xl mb-4">{s.emoji}</div>
          <h2 className="text-2xl font-bold text-white mb-3">{s.title}</h2>
          <p className="text-muted text-sm whitespace-pre-line leading-relaxed">{s.desc}</p>
        </div>

        {/* Progress dots */}
        <div className="flex justify-center space-x-1.5 mb-6">
          {STEPS.map((_, i) => (
            <div key={i} className={`h-1.5 rounded-full transition-all ${
              i === step ? 'w-6 bg-accent' : 'w-1.5 bg-dark-600'
            }`} />
          ))}
        </div>

        <div className="flex space-x-2">
          {step > 0 && (
            <button onClick={() => setStep(step - 1)}
              className="px-4 py-3 bg-dark-700 text-muted text-sm font-medium rounded-2xl hover:bg-dark-600">
              이전
            </button>
          )}
          <button onClick={next}
            className="flex-1 py-3 bg-accent text-white font-semibold rounded-2xl hover:bg-accent-hover active:scale-[0.98] transition-all">
            {step === STEPS.length - 1 ? '거래 시작하기 🚀' : '다음'}
          </button>
        </div>

        <button onClick={close} className="w-full mt-3 py-2 text-dark-400 text-xs hover:text-muted">
          건너뛰기
        </button>
      </div>
    </div>
  );
};

export default WelcomeGuide;
