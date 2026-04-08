import React, { useState, useEffect } from 'react';
import api from '../api';
import { formatUSD, toNum, timeAgo, formatQty } from '../utils';
import { toast } from 'react-toastify';

const History = () => {
  const [tab, setTab] = useState('orders');
  const [orders, setOrders] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  // Alert form
  const [alertSymbol, setAlertSymbol] = useState('BTCUSDT');
  const [alertPrice, setAlertPrice] = useState('');
  const [alertCondition, setAlertCondition] = useState('ABOVE');
  const [alertMemo, setAlertMemo] = useState('');
  const [alertLoading, setAlertLoading] = useState(false);

  const fetchAll = async () => {
    try {
      const [ordRes, txRes, alertRes] = await Promise.all([
        api.get('/orders'),
        api.get('/account/transactions'),
        api.get('/alerts'),
      ]);
      setOrders(ordRes.data);
      setTransactions(txRes.data);
      setAlerts(alertRes.data);
    } catch {
      toast.error('Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, []);

  const handleCancel = async (orderId) => {
    try {
      await api.delete(`/orders/${orderId}`);
      setOrders((prev) => prev.map((o) => o.id === orderId ? { ...o, order_status: 'CANCELLED' } : o));
      toast.success('Order cancelled');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Cancel failed');
    }
  };

  const handleCreateAlert = async (e) => {
    e.preventDefault();
    if (!alertPrice || parseFloat(alertPrice) <= 0) {
      toast.error('Enter a valid price');
      return;
    }
    setAlertLoading(true);
    try {
      await api.post('/alerts', {
        symbol: alertSymbol,
        target_price: parseFloat(alertPrice),
        condition: alertCondition,
        memo: alertMemo,
      });
      toast.success('Alert created');
      setAlertPrice('');
      setAlertMemo('');
      fetchAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create alert');
    } finally {
      setAlertLoading(false);
    }
  };

  const handleDeleteAlert = async (id) => {
    try {
      await api.delete(`/alerts/${id}`);
      setAlerts((prev) => prev.filter((a) => a.id !== id));
      toast.success('Alert deleted');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed');
    }
  };

  const statusBadge = (status) => {
    const styles = {
      FILLED: 'bg-profit/15 text-profit',
      PENDING: 'bg-accent/15 text-accent',
      PARTIALLY_FILLED: 'bg-accent/15 text-accent',
      CANCELLED: 'bg-dark-600 text-dark-400',
    };
    return (
      <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${styles[status] || 'bg-dark-600 text-muted'}`}>
        {status}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="skeleton h-10 w-64 rounded-lg mb-6" />
        {[1,2,3,4,5].map(i => <div key={i} className="skeleton h-14 w-full rounded-lg mb-2" />)}
      </div>
    );
  }

  const pendingOrders = orders.filter(o => o.order_status === 'PENDING');
  const activeAlerts = alerts.filter(a => a.is_active);
  const triggeredAlerts = alerts.filter(a => !a.is_active);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Tabs */}
      <div className="flex items-center space-x-1 bg-dark-800 rounded-lg p-1 w-fit mb-6 border border-dark-600">
        {[
          { key: 'orders', label: 'Orders', count: orders.length },
          { key: 'transactions', label: 'Trades', count: transactions.length },
          { key: 'alerts', label: 'Alerts', count: activeAlerts.length },
        ].map(({ key, label, count }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              tab === key ? 'bg-dark-600 text-white' : 'text-muted hover:text-white'
            }`}
          >
            {label}
            <span className="ml-1.5 text-[10px] text-dark-400">{count}</span>
          </button>
        ))}
      </div>

      {/* Pending orders summary */}
      {tab === 'orders' && pendingOrders.length > 0 && (
        <div className="bg-accent/5 border border-accent/20 rounded-xl p-4 mb-4 fade-in">
          <p className="text-accent text-sm font-medium">
            {pendingOrders.length} pending limit order{pendingOrders.length > 1 ? 's' : ''} waiting for price match
          </p>
        </div>
      )}

      {/* Orders tab */}
      {tab === 'orders' && (
        <div className="bg-dark-800 rounded-xl border border-dark-600 overflow-hidden fade-in">
          {orders.length === 0 ? (
            <div className="p-12 text-center text-muted">No orders yet</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-dark-600">
                    <th className="px-5 py-3 text-left text-[11px] font-medium text-muted uppercase tracking-wider">Time</th>
                    <th className="px-5 py-3 text-left text-[11px] font-medium text-muted uppercase tracking-wider">Pair</th>
                    <th className="px-5 py-3 text-left text-[11px] font-medium text-muted uppercase tracking-wider">Side</th>
                    <th className="px-5 py-3 text-left text-[11px] font-medium text-muted uppercase tracking-wider">Type</th>
                    <th className="px-5 py-3 text-right text-[11px] font-medium text-muted uppercase tracking-wider">Qty</th>
                    <th className="px-5 py-3 text-right text-[11px] font-medium text-muted uppercase tracking-wider">Price</th>
                    <th className="px-5 py-3 text-right text-[11px] font-medium text-muted uppercase tracking-wider">Filled</th>
                    <th className="px-5 py-3 text-center text-[11px] font-medium text-muted uppercase tracking-wider">Status</th>
                    <th className="px-5 py-3 text-center text-[11px] font-medium text-muted uppercase tracking-wider">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-600">
                  {orders.map((o) => (
                    <tr key={o.id} className="hover:bg-dark-700/50 transition-colors">
                      <td className="px-5 py-3 text-muted text-xs whitespace-nowrap">{timeAgo(o.created_at)}</td>
                      <td className="px-5 py-3 text-white text-sm font-medium">{o.symbol}</td>
                      <td className="px-5 py-3">
                        <span className={`text-xs font-bold ${o.side === 'BUY' ? 'text-profit' : 'text-loss'}`}>{o.side}</span>
                      </td>
                      <td className="px-5 py-3 text-muted text-xs">{o.order_type}</td>
                      <td className="px-5 py-3 text-right text-white text-sm font-mono">{formatQty(o.quantity, 4)}</td>
                      <td className="px-5 py-3 text-right text-white text-sm font-mono">
                        {o.price ? formatUSD(o.price) : '-'}
                        {o.filled_price && o.filled_price !== o.price && (
                          <span className="block text-[10px] text-muted">filled: {formatUSD(o.filled_price)}</span>
                        )}
                      </td>
                      <td className="px-5 py-3 text-right text-sm font-mono">
                        <span className="text-white">{formatQty(o.filled_quantity, 4)}</span>
                        <span className="text-dark-500">/{formatQty(o.quantity, 4)}</span>
                        {toNum(o.commission) > 0 && (
                          <span className="block text-[10px] text-muted">fee: {formatUSD(o.commission)}</span>
                        )}
                      </td>
                      <td className="px-5 py-3 text-center">{statusBadge(o.order_status)}</td>
                      <td className="px-5 py-3 text-center">
                        {o.order_status === 'PENDING' && (
                          <button
                            onClick={() => handleCancel(o.id)}
                            className="text-[10px] font-semibold text-loss hover:text-loss/80 uppercase transition-colors"
                          >
                            Cancel
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Transactions tab */}
      {tab === 'transactions' && (
        <div className="bg-dark-800 rounded-xl border border-dark-600 overflow-hidden fade-in">
          {transactions.length === 0 ? (
            <div className="p-12 text-center text-muted">No trades yet</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-dark-600">
                    <th className="px-5 py-3 text-left text-[11px] font-medium text-muted uppercase tracking-wider">Time</th>
                    <th className="px-5 py-3 text-left text-[11px] font-medium text-muted uppercase tracking-wider">Pair</th>
                    <th className="px-5 py-3 text-left text-[11px] font-medium text-muted uppercase tracking-wider">Side</th>
                    <th className="px-5 py-3 text-right text-[11px] font-medium text-muted uppercase tracking-wider">Qty</th>
                    <th className="px-5 py-3 text-right text-[11px] font-medium text-muted uppercase tracking-wider">Price</th>
                    <th className="px-5 py-3 text-right text-[11px] font-medium text-muted uppercase tracking-wider">Total</th>
                    <th className="px-5 py-3 text-right text-[11px] font-medium text-muted uppercase tracking-wider">Fee</th>
                    <th className="px-5 py-3 text-right text-[11px] font-medium text-muted uppercase tracking-wider">P&L</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-600">
                  {transactions.map((tx) => {
                    const total = toNum(tx.price) * toNum(tx.quantity);
                    const pnl = toNum(tx.realized_pnl);
                    return (
                      <tr key={tx.id} className="hover:bg-dark-700/50 transition-colors">
                        <td className="px-5 py-3 text-muted text-xs whitespace-nowrap">{timeAgo(tx.timestamp)}</td>
                        <td className="px-5 py-3 text-white text-sm font-medium">{tx.symbol}</td>
                        <td className="px-5 py-3">
                          <span className={`text-xs font-bold ${tx.side === 'BUY' ? 'text-profit' : 'text-loss'}`}>{tx.side}</span>
                          <span className="block text-[9px] text-dark-400">{tx.is_maker ? 'maker' : 'taker'}</span>
                        </td>
                        <td className="px-5 py-3 text-right text-white text-sm font-mono">{formatQty(tx.quantity, 4)}</td>
                        <td className="px-5 py-3 text-right text-white text-sm font-mono">{formatUSD(tx.price)}</td>
                        <td className="px-5 py-3 text-right text-white text-sm font-mono">{formatUSD(total)}</td>
                        <td className="px-5 py-3 text-right text-muted text-sm font-mono">
                          {formatUSD(tx.fee)}
                          <span className="block text-[9px] text-dark-400">{tx.fee_asset}</span>
                        </td>
                        <td className={`px-5 py-3 text-right text-sm font-mono font-medium ${pnl > 0 ? 'text-profit' : pnl < 0 ? 'text-loss' : 'text-muted'}`}>
                          {pnl !== 0 ? (pnl > 0 ? '+' : '') + formatUSD(tx.realized_pnl) : '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Alerts tab */}
      {tab === 'alerts' && (
        <div className="space-y-4 fade-in">
          {/* Create alert form */}
          <div className="bg-dark-800 rounded-xl border border-dark-600 p-5">
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">New Price Alert</h3>
            <form onSubmit={handleCreateAlert} className="flex flex-wrap gap-3 items-end">
              <div className="flex-1 min-w-[120px]">
                <label className="block text-muted text-[10px] font-medium mb-1.5 uppercase tracking-wider">Symbol</label>
                <select
                  value={alertSymbol}
                  onChange={(e) => setAlertSymbol(e.target.value)}
                  className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-lg text-white text-sm focus:outline-none focus:border-accent transition-colors"
                >
                  <option value="BTCUSDT">BTC/USDT</option>
                  <option value="ETHUSDT">ETH/USDT</option>
                  <option value="BNBUSDT">BNB/USDT</option>
                </select>
              </div>
              <div className="flex-1 min-w-[100px]">
                <label className="block text-muted text-[10px] font-medium mb-1.5 uppercase tracking-wider">When price</label>
                <select
                  value={alertCondition}
                  onChange={(e) => setAlertCondition(e.target.value)}
                  className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-lg text-white text-sm focus:outline-none focus:border-accent transition-colors"
                >
                  <option value="ABOVE">Goes above</option>
                  <option value="BELOW">Goes below</option>
                </select>
              </div>
              <div className="flex-1 min-w-[140px]">
                <label className="block text-muted text-[10px] font-medium mb-1.5 uppercase tracking-wider">Target Price</label>
                <input
                  type="number"
                  step="any"
                  value={alertPrice}
                  onChange={(e) => setAlertPrice(e.target.value)}
                  className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-lg text-white text-sm font-mono placeholder-dark-500 focus:outline-none focus:border-accent transition-colors"
                  placeholder="0.00"
                  required
                />
              </div>
              <div className="flex-1 min-w-[120px]">
                <label className="block text-muted text-[10px] font-medium mb-1.5 uppercase tracking-wider">Memo (optional)</label>
                <input
                  type="text"
                  value={alertMemo}
                  onChange={(e) => setAlertMemo(e.target.value)}
                  className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-lg text-white text-sm placeholder-dark-500 focus:outline-none focus:border-accent transition-colors"
                  placeholder="e.g. buy signal"
                />
              </div>
              <button
                type="submit"
                disabled={alertLoading}
                className="px-5 py-2.5 bg-accent text-dark-900 font-semibold rounded-lg text-sm hover:bg-accent-hover active:scale-[0.98] transition-all disabled:opacity-50"
              >
                {alertLoading ? 'Creating...' : 'Create Alert'}
              </button>
            </form>
          </div>

          {/* Active alerts */}
          {activeAlerts.length > 0 && (
            <div className="bg-dark-800 rounded-xl border border-dark-600 overflow-hidden">
              <div className="px-5 py-3 border-b border-dark-600">
                <h3 className="text-sm font-semibold text-white uppercase tracking-wider">
                  Active Alerts
                  <span className="ml-2 text-[10px] text-accent font-normal">{activeAlerts.length}</span>
                </h3>
              </div>
              <div className="divide-y divide-dark-600">
                {activeAlerts.map((a) => (
                  <div key={a.id} className="flex items-center justify-between px-5 py-3 hover:bg-dark-700/50 transition-colors">
                    <div className="flex items-center space-x-4">
                      <div className="w-8 h-8 bg-accent/15 rounded-full flex items-center justify-center">
                        <span className="text-accent text-[10px] font-bold">{a.symbol.replace('USDT', '').slice(0, 3)}</span>
                      </div>
                      <div>
                        <p className="text-white text-sm">
                          {a.symbol} <span className={`text-xs ${a.condition === 'ABOVE' ? 'text-profit' : 'text-loss'}`}>{a.condition === 'ABOVE' ? 'rises above' : 'drops below'}</span>{' '}
                          <span className="font-mono font-medium">{formatUSD(a.target_price)}</span>
                        </p>
                        {a.memo && <p className="text-muted text-xs mt-0.5">{a.memo}</p>}
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className="flex items-center space-x-1 text-[10px] text-accent">
                        <span className="w-1.5 h-1.5 rounded-full bg-accent pulse-dot" />
                        <span>Watching</span>
                      </span>
                      <button
                        onClick={() => handleDeleteAlert(a.id)}
                        className="text-muted hover:text-loss text-xs transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Triggered alerts */}
          {triggeredAlerts.length > 0 && (
            <div className="bg-dark-800 rounded-xl border border-dark-600 overflow-hidden">
              <div className="px-5 py-3 border-b border-dark-600">
                <h3 className="text-sm font-semibold text-muted uppercase tracking-wider">Triggered</h3>
              </div>
              <div className="divide-y divide-dark-600">
                {triggeredAlerts.map((a) => (
                  <div key={a.id} className="flex items-center justify-between px-5 py-3 opacity-60">
                    <div className="flex items-center space-x-4">
                      <div className="w-8 h-8 bg-dark-600 rounded-full flex items-center justify-center">
                        <span className="text-muted text-[10px] font-bold">{a.symbol.replace('USDT', '').slice(0, 3)}</span>
                      </div>
                      <div>
                        <p className="text-muted text-sm">
                          {a.symbol} {a.condition === 'ABOVE' ? 'rose above' : 'dropped below'} {formatUSD(a.target_price)}
                        </p>
                        <p className="text-dark-500 text-xs">{a.triggered_at ? timeAgo(a.triggered_at) : ''}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteAlert(a.id)}
                      className="text-muted hover:text-loss text-xs transition-colors"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeAlerts.length === 0 && triggeredAlerts.length === 0 && (
            <div className="bg-dark-800 rounded-xl border border-dark-600 p-12 text-center">
              <p className="text-muted mb-1">No alerts yet</p>
              <p className="text-dark-500 text-sm">Create an alert above to get notified when price reaches your target</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default History;
