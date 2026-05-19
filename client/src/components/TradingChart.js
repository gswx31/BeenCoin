import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts';
import api from '../api';
import { getWsUrl } from '../utils';

const INTERVALS = [
  { key: '1m', label: '1분' },
  { key: '5m', label: '5분' },
  { key: '15m', label: '15분' },
  { key: '1h', label: '1시간' },
  { key: '4h', label: '4시간' },
  { key: '1d', label: '1일' },
  { key: '1w', label: '1주' },
];

const INDICATORS = [
  { key: 'ma20', label: 'MA20', color: '#f7931a' },
  { key: 'ma60', label: 'MA60', color: '#7ee8c7' },
  { key: 'ma120', label: 'MA120', color: '#c4b5fd' },
  { key: 'bb', label: '볼린저', color: '#ff9a9e' },
];

const TradingChart = ({ symbol = 'BTCUSDT', onPriceUpdate }) => {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const candleRef = useRef(null);
  const volumeRef = useRef(null);
  const indicatorSeriesRef = useRef({});
  const wsRef = useRef(null);
  const [interval, setIntervalState] = useState('1h');
  const [loading, setLoading] = useState(true);
  const [activeIndicators, setActiveIndicators] = useState(new Set(['ma20']));

  // Create chart
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#161b22' },
        textColor: '#8b949e',
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: 'rgba(43,49,57,0.3)' },
        horzLines: { color: 'rgba(43,49,57,0.3)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: 'rgba(247,147,26,0.4)', width: 1, style: 2 },
        horzLine: { color: 'rgba(247,147,26,0.4)', width: 1, style: 2 },
      },
      rightPriceScale: { borderColor: '#21262d', scaleMargins: { top: 0.1, bottom: 0.2 } },
      timeScale: { borderColor: '#21262d', timeVisible: true, secondsVisible: false },
    });

    candleRef.current = chart.addCandlestickSeries({
      upColor: '#3fb68b', downColor: '#f0616d',
      borderUpColor: '#3fb68b', borderDownColor: '#f0616d',
      wickUpColor: '#3fb68b', wickDownColor: '#f0616d',
    });

    volumeRef.current = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
      scaleMargins: { top: 0.8, bottom: 0 },
    });
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });

    chartRef.current = chart;

    const handleResize = () => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
      indicatorSeriesRef.current = {};
    };
  }, []);

  // Fetch klines + indicators
  useEffect(() => {
    if (!candleRef.current) return;
    setLoading(true);

    api.get(`/market/indicators?symbol=${symbol}&interval=${interval}&limit=300`)
      .then(({ data }) => {
        const klines = data.klines || [];
        candleRef.current.setData(klines.map(k => ({ time: k.time, open: k.open, high: k.high, low: k.low, close: k.close })));
        volumeRef.current.setData(klines.map(k => ({
          time: k.time, value: k.volume,
          color: k.close >= k.open ? 'rgba(63,182,139,0.3)' : 'rgba(240,97,109,0.3)',
        })));
        if (klines.length > 0) onPriceUpdate?.(klines[klines.length - 1].close);
        applyIndicators(data.indicators);
        chartRef.current?.timeScale().fitContent();
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, interval]);

  // Re-apply indicators when toggled
  useEffect(() => {
    if (!chartRef.current) return;
    api.get(`/market/indicators?symbol=${symbol}&interval=${interval}&limit=300`)
      .then(({ data }) => applyIndicators(data.indicators))
      .catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeIndicators]);

  function applyIndicators(ind) {
    if (!chartRef.current || !ind) return;
    const chart = chartRef.current;

    // 모든 기존 지표 시리즈 제거
    Object.entries(indicatorSeriesRef.current).forEach(([key, series]) => {
      try { chart.removeSeries(series); } catch {}
    });
    indicatorSeriesRef.current = {};

    const addLine = (key, data, color, width = 1) => {
      const s = chart.addLineSeries({ color, lineWidth: width, priceLineVisible: false, lastValueVisible: false });
      s.setData(data);
      indicatorSeriesRef.current[key] = s;
    };

    if (activeIndicators.has('ma20')) addLine('ma20', ind.ma20, '#f7931a');
    if (activeIndicators.has('ma60')) addLine('ma60', ind.ma60, '#7ee8c7');
    if (activeIndicators.has('ma120')) addLine('ma120', ind.ma120, '#c4b5fd');
    if (activeIndicators.has('bb')) {
      addLine('bb_upper', ind.bb_upper, 'rgba(255,154,158,0.7)');
      addLine('bb_middle', ind.bb_middle, 'rgba(255,154,158,0.4)');
      addLine('bb_lower', ind.bb_lower, 'rgba(255,154,158,0.7)');
    }
  }

  function toggleIndicator(key) {
    setActiveIndicators(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  }

  // WebSocket real-time
  useEffect(() => {
    wsRef.current?.close();
    const ws = new WebSocket(getWsUrl(`/ws/prices/${symbol}`));
    wsRef.current = ws;
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (!data.price) return;
      const price = parseFloat(data.price);
      const now = Math.floor(Date.now() / 1000);
      onPriceUpdate?.(price);
      if (candleRef.current) {
        candleRef.current.update({ time: now, open: price, high: price, low: price, close: price });
      }
    };
    ws.onerror = () => ws.close();
    return () => ws.close();
  }, [symbol, onPriceUpdate]);

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="flex items-center space-x-1">
          {INTERVALS.map(({ key, label }) => (
            <button key={key} onClick={() => setIntervalState(key)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors ${
                interval === key ? 'bg-dark-600 text-white' : 'text-dark-400 hover:text-muted'
              }`}>{label}</button>
          ))}
        </div>
        <div className="flex items-center space-x-1">
          {INDICATORS.map(({ key, label, color }) => (
            <button key={key} onClick={() => toggleIndicator(key)}
              className={`px-2 py-1 rounded-lg text-[10px] font-medium transition-all flex items-center space-x-1 ${
                activeIndicators.has(key) ? 'bg-dark-700 text-white' : 'text-dark-500 hover:text-muted'
              }`}>
              <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-dark-800/80 z-10 rounded-xl">
            <span className="text-muted text-sm animate-pulse">차트 불러오는 중...</span>
          </div>
        )}
        <div ref={containerRef} className="h-[350px] sm:h-[420px] rounded-xl overflow-hidden" />
      </div>
    </div>
  );
};

export default TradingChart;
