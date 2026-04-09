import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts';
import api from '../api';
import { getWsUrl } from '../utils';

const INTERVALS = [
  { key: '1m', label: '1m' },
  { key: '5m', label: '5m' },
  { key: '15m', label: '15m' },
  { key: '1h', label: '1H' },
  { key: '4h', label: '4H' },
  { key: '1d', label: '1D' },
  { key: '1w', label: '1W' },
];

const TradingChart = ({ symbol = 'BTCUSDT', onPriceUpdate }) => {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const wsRef = useRef(null);
  const [interval, setInterval_] = useState('1h');
  const [loading, setLoading] = useState(true);

  // Create chart once
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#12161c' },
        textColor: '#848e9c',
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: 'rgba(43,49,57,0.3)' },
        horzLines: { color: 'rgba(43,49,57,0.3)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: 'rgba(240,185,11,0.4)', width: 1, style: 2 },
        horzLine: { color: 'rgba(240,185,11,0.4)', width: 1, style: 2 },
      },
      rightPriceScale: {
        borderColor: '#2b3139',
        scaleMargins: { top: 0.1, bottom: 0.2 },
      },
      timeScale: {
        borderColor: '#2b3139',
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: true,
      handleScale: true,
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#0ecb81',
      downColor: '#f6465d',
      borderUpColor: '#0ecb81',
      borderDownColor: '#f6465d',
      wickUpColor: '#0ecb81',
      wickDownColor: '#f6465d',
    });

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  // Fetch klines when symbol or interval changes
  useEffect(() => {
    if (!candleSeriesRef.current) return;

    setLoading(true);
    api.get(`/market/klines?symbol=${symbol}&interval=${interval}&limit=300`)
      .then(({ data }) => {
        if (!Array.isArray(data)) return;
        candleSeriesRef.current.setData(data.map(k => ({
          time: k.time,
          open: k.open,
          high: k.high,
          low: k.low,
          close: k.close,
        })));
        volumeSeriesRef.current.setData(data.map(k => ({
          time: k.time,
          value: k.volume,
          color: k.close >= k.open ? 'rgba(14,203,129,0.3)' : 'rgba(246,70,93,0.3)',
        })));
        if (data.length > 0) {
          const last = data[data.length - 1];
          onPriceUpdate?.(last.close);
        }
        chartRef.current?.timeScale().fitContent();
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [symbol, interval, onPriceUpdate]);

  // WebSocket for real-time updates
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

      // Update the last candle's close in real-time
      if (candleSeriesRef.current) {
        candleSeriesRef.current.update({
          time: now,
          open: price,
          high: price,
          low: price,
          close: price,
        });
      }
    };

    ws.onerror = () => ws.close();
    return () => ws.close();
  }, [symbol, onPriceUpdate]);

  return (
    <div className="relative">
      {/* Interval selector */}
      <div className="flex items-center space-x-1 mb-3">
        {INTERVALS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setInterval_(key)}
            className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
              interval === key
                ? 'bg-dark-600 text-white'
                : 'text-dark-400 hover:text-muted'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div className="relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-dark-800/80 z-10 rounded-lg">
            <span className="text-muted text-sm animate-pulse">Loading chart...</span>
          </div>
        )}
        <div ref={chartContainerRef} className="h-[350px] sm:h-[420px] rounded-lg overflow-hidden" />
      </div>
    </div>
  );
};

export default TradingChart;
