export function formatUSD(value) {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (num == null || isNaN(num)) return '$0.00';
  const abs = Math.abs(num);
  if (abs >= 1_000_000) {
    return (num < 0 ? '-' : '') + '$' + (abs / 1_000_000).toFixed(2) + 'M';
  }
  return '$' + num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatPrice(value) {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (num == null || isNaN(num)) return '$0.00';
  if (num >= 1000) {
    return '$' + num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return '$' + num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
}

export function formatPercent(value) {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (num == null || isNaN(num)) return '0.00%';
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '%';
}

export function formatQty(value, decimals = 6) {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (num == null || isNaN(num)) return '0';
  return num.toFixed(decimals);
}

export function toNum(value) {
  if (typeof value === 'number') return value;
  const n = parseFloat(value);
  return isNaN(n) ? 0 : n;
}

export function getWsUrl(path) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.hostname;
  const port = process.env.REACT_APP_WS_PORT || '8000';
  const token = localStorage.getItem('token') || '';
  return `${protocol}//${host}:${port}/api/v1${path}?token=${token}`;
}

export function timeAgo(dateStr) {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now - date) / 1000);
  if (diff < 60) return 'Just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function signedFormat(value, formatter = formatUSD) {
  const num = toNum(value);
  const prefix = num >= 0 ? '+' : '';
  return prefix + formatter(value);
}
