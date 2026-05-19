import React, { useState } from 'react';

const HelpTooltip = ({ text }) => {
  const [show, setShow] = useState(false);
  return (
    <span className="relative inline-block ml-1">
      <button type="button"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onClick={() => setShow(!show)}
        className="w-4 h-4 rounded-full bg-dark-600 text-dark-300 text-[9px] font-bold inline-flex items-center justify-center hover:bg-dark-500 hover:text-white">
        ?
      </button>
      {show && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 p-3 bg-dark-900 border border-dark-600 rounded-xl text-[11px] text-white leading-relaxed z-50 shadow-xl">
          {text}
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 w-2 h-2 bg-dark-900 border-r border-b border-dark-600 rotate-45" />
        </div>
      )}
    </span>
  );
};

export default HelpTooltip;
