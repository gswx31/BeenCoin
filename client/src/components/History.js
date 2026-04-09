import React, { useState, useEffect } from 'react';
import api from '../api';
import { formatUSD, toNum, timeAgo, formatQty } from '../utils';
import { toast } from 'react-toastify';

const STATUS_KR = { FILLED: '체결', PENDING: '대기중', PARTIALLY_FILLED: '부분체결', CANCELLED: '취소됨' };
const SIDE_KR = { BUY: '매수', SELL: '매도' };
const TYPE_KR = { MARKET: '시장가', LIMIT: '지정가', STOP_LOSS_LIMIT: '손절매', TAKE_PROFIT_LIMIT: '익절매' };

const History = () => {
  const [tab, setTab] = useState('orders');
  const [orders, setOrders] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [alertSymbol, setAlertSymbol] = useState('BTCUSDT');
  const [alertPrice, setAlertPrice] = useState('');
  const [alertCondition, setAlertCondition] = useState('ABOVE');
  const [alertMemo, setAlertMemo] = useState('');
  const [alertLoading, setAlertLoading] = useState(false);

  const fetchAll = async () => {
    try {
      const [o, t, a] = await Promise.all([api.get('/orders'), api.get('/account/transactions'), api.get('/alerts')]);
      setOrders(o.data); setTransactions(t.data); setAlerts(a.data);
    } catch { toast.error('내역을 불러올 수 없어요'); }
    finally { setLoading(false); }
  };
  useEffect(() => { fetchAll(); }, []);

  const handleCancel = async (id) => {
    try { await api.delete(`/orders/${id}`); setOrders(p => p.map(o => o.id === id ? { ...o, order_status: 'CANCELLED' } : o)); toast.success('주문이 취소됐어요'); }
    catch (e) { toast.error(e.response?.data?.detail || '취소 실패'); }
  };

  const handleCreateAlert = async (e) => {
    e.preventDefault();
    if (!alertPrice || parseFloat(alertPrice) <= 0) { toast.error('가격을 입력해주세요'); return; }
    setAlertLoading(true);
    try {
      await api.post('/alerts', { symbol: alertSymbol, target_price: parseFloat(alertPrice), condition: alertCondition, memo: alertMemo });
      toast.success('알림이 설정됐어요! 🔔'); setAlertPrice(''); setAlertMemo(''); fetchAll();
    } catch (e) { toast.error(e.response?.data?.detail || '알림 생성 실패'); }
    finally { setAlertLoading(false); }
  };

  const handleDeleteAlert = async (id) => {
    try { await api.delete(`/alerts/${id}`); setAlerts(p => p.filter(a => a.id !== id)); toast.success('알림 삭제 완료'); }
    catch { toast.error('삭제 실패'); }
  };

  const statusBadge = (s) => {
    const styles = { FILLED: 'bg-profit-soft text-profit', PENDING: 'bg-accent-soft text-accent', PARTIALLY_FILLED: 'bg-accent-soft text-accent', CANCELLED: 'bg-dark-600 text-dark-400' };
    return <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold ${styles[s] || 'bg-dark-600 text-muted'}`}>{STATUS_KR[s] || s}</span>;
  };

  if (loading) return <div className="max-w-7xl mx-auto px-4 py-6">{[1,2,3,4,5].map(i => <div key={i} className="skeleton h-14 w-full rounded-2xl mb-2" />)}</div>;

  const pendingOrders = orders.filter(o => o.order_status === 'PENDING');
  const activeAlerts = alerts.filter(a => a.is_active);
  const triggeredAlerts = alerts.filter(a => !a.is_active);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div className="flex items-center space-x-1 bg-dark-800 rounded-xl p-1 w-fit mb-6 border border-dark-600">
        {[{ key: 'orders', label: '📋 주문', count: orders.length }, { key: 'transactions', label: '💱 체결', count: transactions.length }, { key: 'alerts', label: '🔔 알림', count: activeAlerts.length }].map(({ key, label, count }) => (
          <button key={key} onClick={() => setTab(key)} className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${tab === key ? 'bg-dark-600 text-white' : 'text-muted hover:text-white'}`}>
            {label}<span className="ml-1.5 text-[10px] text-dark-400">{count}</span>
          </button>
        ))}
      </div>

      {tab === 'orders' && pendingOrders.length > 0 && (
        <div className="bg-accent-soft border border-accent/20 rounded-2xl p-4 mb-4 fade-in">
          <p className="text-accent text-sm font-medium">⏳ {pendingOrders.length}개의 지정가 주문이 체결 대기중이에요</p>
        </div>
      )}

      {tab === 'orders' && (
        <div className="bg-dark-800 rounded-2xl border border-dark-600 overflow-hidden fade-in">
          {orders.length === 0 ? <div className="p-12 text-center text-muted">아직 주문 내역이 없어요</div> : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead><tr className="border-b border-dark-600">
                  <th className="px-5 py-3 text-left text-[11px] font-medium text-muted">시간</th>
                  <th className="px-5 py-3 text-left text-[11px] font-medium text-muted">코인</th>
                  <th className="px-5 py-3 text-left text-[11px] font-medium text-muted">구분</th>
                  <th className="px-5 py-3 text-left text-[11px] font-medium text-muted">유형</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted">수량</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted">가격</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted">체결</th>
                  <th className="px-5 py-3 text-center text-[11px] font-medium text-muted">상태</th>
                  <th className="px-5 py-3 text-center text-[11px] font-medium text-muted"></th>
                </tr></thead>
                <tbody className="divide-y divide-dark-600">
                  {orders.map((o) => (
                    <tr key={o.id} className="hover:bg-dark-700/50 transition-colors">
                      <td className="px-5 py-3 text-muted text-xs whitespace-nowrap">{timeAgo(o.created_at)}</td>
                      <td className="px-5 py-3 text-white text-sm font-medium">{o.symbol}</td>
                      <td className="px-5 py-3"><span className={`text-xs font-bold ${o.side === 'BUY' ? 'text-profit' : 'text-loss'}`}>{SIDE_KR[o.side]}</span></td>
                      <td className="px-5 py-3 text-muted text-xs">{TYPE_KR[o.order_type] || o.order_type}</td>
                      <td className="px-5 py-3 text-right text-white text-sm font-mono">{formatQty(o.quantity, 4)}</td>
                      <td className="px-5 py-3 text-right text-white text-sm font-mono">
                        {o.price ? formatUSD(o.price) : '-'}
                        {o.filled_price && o.filled_price !== o.price && <span className="block text-[10px] text-muted">체결가: {formatUSD(o.filled_price)}</span>}
                      </td>
                      <td className="px-5 py-3 text-right text-sm font-mono">
                        <span className="text-white">{formatQty(o.filled_quantity, 4)}</span><span className="text-dark-500">/{formatQty(o.quantity, 4)}</span>
                        {toNum(o.commission) > 0 && <span className="block text-[10px] text-muted">수수료: {formatUSD(o.commission)}</span>}
                      </td>
                      <td className="px-5 py-3 text-center">{statusBadge(o.order_status)}</td>
                      <td className="px-5 py-3 text-center">
                        {o.order_status === 'PENDING' && <button onClick={() => handleCancel(o.id)} className="text-[10px] font-semibold text-loss hover:text-loss/80">취소</button>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === 'transactions' && (
        <div className="bg-dark-800 rounded-2xl border border-dark-600 overflow-hidden fade-in">
          {transactions.length === 0 ? <div className="p-12 text-center text-muted">아직 체결 내역이 없어요</div> : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead><tr className="border-b border-dark-600">
                  <th className="px-5 py-3 text-left text-[11px] font-medium text-muted">시간</th>
                  <th className="px-5 py-3 text-left text-[11px] font-medium text-muted">코인</th>
                  <th className="px-5 py-3 text-left text-[11px] font-medium text-muted">구분</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted">수량</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted">가격</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted">금액</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted">수수료</th>
                  <th className="px-5 py-3 text-right text-[11px] font-medium text-muted">실현손익</th>
                </tr></thead>
                <tbody className="divide-y divide-dark-600">
                  {transactions.map((tx) => {
                    const total = toNum(tx.price) * toNum(tx.quantity);
                    const pnl = toNum(tx.realized_pnl);
                    return (
                      <tr key={tx.id} className="hover:bg-dark-700/50 transition-colors">
                        <td className="px-5 py-3 text-muted text-xs whitespace-nowrap">{timeAgo(tx.timestamp)}</td>
                        <td className="px-5 py-3 text-white text-sm font-medium">{tx.symbol}</td>
                        <td className="px-5 py-3">
                          <span className={`text-xs font-bold ${tx.side === 'BUY' ? 'text-profit' : 'text-loss'}`}>{SIDE_KR[tx.side]}</span>
                          <span className="block text-[9px] text-dark-400">{tx.is_maker ? '메이커' : '테이커'}</span>
                        </td>
                        <td className="px-5 py-3 text-right text-white text-sm font-mono">{formatQty(tx.quantity, 4)}</td>
                        <td className="px-5 py-3 text-right text-white text-sm font-mono">{formatUSD(tx.price)}</td>
                        <td className="px-5 py-3 text-right text-white text-sm font-mono">{formatUSD(total)}</td>
                        <td className="px-5 py-3 text-right text-muted text-sm font-mono">{formatUSD(tx.fee)}</td>
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

      {tab === 'alerts' && (
        <div className="space-y-4 fade-in">
          <div className="bg-dark-800 rounded-2xl border border-dark-600 p-5">
            <h3 className="text-sm font-semibold text-white mb-4">🔔 새 가격 알림</h3>
            <form onSubmit={handleCreateAlert} className="flex flex-wrap gap-3 items-end">
              <div className="flex-1 min-w-[120px]">
                <label className="block text-muted text-[10px] font-medium mb-1.5">코인</label>
                <select value={alertSymbol} onChange={(e) => setAlertSymbol(e.target.value)} className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white text-sm focus:outline-none focus:border-accent">
                  <option value="BTCUSDT">BTC/USDT</option><option value="ETHUSDT">ETH/USDT</option><option value="BNBUSDT">BNB/USDT</option>
                </select>
              </div>
              <div className="flex-1 min-w-[100px]">
                <label className="block text-muted text-[10px] font-medium mb-1.5">조건</label>
                <select value={alertCondition} onChange={(e) => setAlertCondition(e.target.value)} className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white text-sm focus:outline-none focus:border-accent">
                  <option value="ABOVE">이상 도달 시</option><option value="BELOW">이하 도달 시</option>
                </select>
              </div>
              <div className="flex-1 min-w-[140px]">
                <label className="block text-muted text-[10px] font-medium mb-1.5">목표 가격</label>
                <input type="number" step="any" value={alertPrice} onChange={(e) => setAlertPrice(e.target.value)} className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white text-sm font-mono placeholder-dark-500 focus:outline-none focus:border-accent" placeholder="0.00" required />
              </div>
              <div className="flex-1 min-w-[120px]">
                <label className="block text-muted text-[10px] font-medium mb-1.5">메모 (선택)</label>
                <input type="text" value={alertMemo} onChange={(e) => setAlertMemo(e.target.value)} className="w-full px-3 py-2.5 bg-dark-700 border border-dark-600 rounded-xl text-white text-sm placeholder-dark-500 focus:outline-none focus:border-accent" placeholder="예: 매수 타이밍" />
              </div>
              <button type="submit" disabled={alertLoading} className="px-5 py-2.5 bg-accent text-white font-semibold rounded-xl text-sm hover:bg-accent-hover active:scale-[0.98] transition-all disabled:opacity-50">
                {alertLoading ? '생성중...' : '알림 만들기'}
              </button>
            </form>
          </div>

          {activeAlerts.length > 0 && (
            <div className="bg-dark-800 rounded-2xl border border-dark-600 overflow-hidden">
              <div className="px-5 py-3 border-b border-dark-600"><h3 className="text-sm font-semibold text-white">활성 알림 <span className="text-[10px] text-accent ml-1">{activeAlerts.length}</span></h3></div>
              <div className="divide-y divide-dark-600">
                {activeAlerts.map((a) => (
                  <div key={a.id} className="flex items-center justify-between px-5 py-3 hover:bg-dark-700/50">
                    <div className="flex items-center space-x-4">
                      <div className="w-8 h-8 bg-accent/15 rounded-xl flex items-center justify-center"><span className="text-accent text-[10px] font-bold">{a.symbol.replace('USDT', '').slice(0, 3)}</span></div>
                      <div>
                        <p className="text-white text-sm">{a.symbol} <span className={`text-xs ${a.condition === 'ABOVE' ? 'text-profit' : 'text-loss'}`}>{a.condition === 'ABOVE' ? '이상 상승' : '이하 하락'}</span> <span className="font-mono font-medium">{formatUSD(a.target_price)}</span></p>
                        {a.memo && <p className="text-muted text-xs mt-0.5">{a.memo}</p>}
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className="flex items-center space-x-1 text-[10px] text-accent"><span className="w-1.5 h-1.5 rounded-full bg-accent pulse-dot" /><span>감시중</span></span>
                      <button onClick={() => handleDeleteAlert(a.id)} className="text-muted hover:text-loss text-xs">삭제</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {triggeredAlerts.length > 0 && (
            <div className="bg-dark-800 rounded-2xl border border-dark-600 overflow-hidden">
              <div className="px-5 py-3 border-b border-dark-600"><h3 className="text-sm font-semibold text-muted">발동된 알림</h3></div>
              <div className="divide-y divide-dark-600">
                {triggeredAlerts.map((a) => (
                  <div key={a.id} className="flex items-center justify-between px-5 py-3 opacity-60">
                    <div className="flex items-center space-x-4">
                      <div className="w-8 h-8 bg-dark-600 rounded-xl flex items-center justify-center"><span className="text-muted text-[10px] font-bold">{a.symbol.replace('USDT', '').slice(0, 3)}</span></div>
                      <div>
                        <p className="text-muted text-sm">{a.symbol} {a.condition === 'ABOVE' ? '상승 돌파' : '하락 돌파'} {formatUSD(a.target_price)}</p>
                        <p className="text-dark-500 text-xs">{a.triggered_at ? timeAgo(a.triggered_at) : ''}</p>
                      </div>
                    </div>
                    <button onClick={() => handleDeleteAlert(a.id)} className="text-muted hover:text-loss text-xs">삭제</button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeAlerts.length === 0 && triggeredAlerts.length === 0 && (
            <div className="bg-dark-800 rounded-2xl border border-dark-600 p-12 text-center">
              <div className="text-3xl mb-3">🔔</div>
              <p className="text-muted mb-1">아직 설정된 알림이 없어요</p>
              <p className="text-dark-500 text-sm">위에서 알림을 만들어보세요!</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default History;
