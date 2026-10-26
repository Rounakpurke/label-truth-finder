import { useEffect, useState } from 'react';
import { LayoutDashboard, ScanSearch, History as HistIcon, MessageSquare, Settings as Cog, Menu, Leaf, Lock } from 'lucide-react';
import Dashboard from './pages/Dashboard.jsx';
import Analyze from './pages/Analyze.jsx';
import History from './pages/History.jsx';
import Reviews from './pages/Reviews.jsx';
import Settings from './pages/Settings.jsx';
import { mockHistory } from './mock/mockData';
import { Notice } from './components/ui.jsx';
import { USE_MOCK, getAnalysisHistory, clearAnalysisHistory } from './services/api';

const NAV = [
  ['dashboard', 'Dashboard', LayoutDashboard, 'Understand what’s inside your products.'],
  ['analyze', 'Analyze Product', ScanSearch, 'Upload a label photo or search by barcode or name.'],
  ['history', 'Analysis History', HistIcon, 'Reopen reports from earlier analyses.'],
  ['reviews', 'Community Reviews', MessageSquare, 'Personal opinions from other shoppers.'],
  ['settings', 'Settings', Cog, 'Region, category and privacy controls.'],
];
const load = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } };

export default function App() {
  const [page, setPage] = useState('dashboard');
  const [menu, setMenu] = useState(false);
  const [settings, setSettings] = useState(() => load('ltf-settings', { country: 'India', category: '' }));
  const [history, setHistory] = useState(() => (USE_MOCK ? load('ltf-history', mockHistory) : []));
  const [historyError, setHistoryError] = useState('');
  const [report, setReport] = useState(null);

  useEffect(() => { try { localStorage.setItem('ltf-settings', JSON.stringify(settings)); } catch {} }, [settings]);
  // Demo mode keeps history in localStorage; real mode loads it from the backend database.
  useEffect(() => { if (USE_MOCK) { try { localStorage.setItem('ltf-history', JSON.stringify(history)); } catch {} } }, [history]);
  const refreshHistory = () => getAnalysisHistory().then((h) => { setHistory(h); setHistoryError(''); })
    .catch((e) => setHistoryError(`Could not load saved analyses: ${e.message}`));
  useEffect(() => { if (!USE_MOCK) refreshHistory(); }, []);

  const go = (p) => { setPage(p); setMenu(false); };
  const onDone = (data, thumbnail) => {
    setReport(data);
    if (!USE_MOCK) { refreshHistory(); return; }
    setHistory((h) => [{ id: `a-${Date.now()}`, product_name: data.product_name || 'Unnamed product', thumbnail: null, date: new Date().toISOString().slice(0, 10), status: 'Completed', demo: !!data.demo, report: data }, ...h]);
  };
  const clearHistory = async () => {
    try { if (!USE_MOCK) await clearAnalysisHistory(); setHistory([]); setHistoryError(''); }
    catch (e) { setHistoryError(`Could not clear history: ${e.message}`); }
  };
  const openReport = (h) => { setReport(h.report); go('analyze'); };
  const current = NAV.find((n) => n[0] === page);

  return (
    <div className="shell">
      <aside className={`side ${menu ? 'open' : ''}`}>
        <div className="brand"><Leaf size={22} /> <span>Label Truth Finder</span></div>
        <nav>{NAV.map(([id, label, Icon]) => <button key={id} className={page === id ? 'on' : ''} onClick={() => go(id)}><Icon size={18} /> {label}</button>)}</nav>
        <div className="privacy"><Lock size={14} /> {USE_MOCK ? 'Demo mode: no backend is used and no images leave your browser.' : 'Photos are analyzed by an AI model on your own computer and are not saved. Reports are stored in a local database file.'}</div>
      </aside>
      <main>
        <header>
          <button className="burger" aria-label="Toggle navigation" onClick={() => setMenu(!menu)}><Menu size={22} /></button>
          <div><h1>{current[1]}</h1><p className="muted">{current[3]}</p></div>
        </header>
        <div className="content">
          {historyError && <Notice tone="error">{historyError} Check that the backend is running.</Notice>}
          {page === 'dashboard' && <Dashboard history={history} go={go} openReport={openReport} />}
          {page === 'analyze' && <Analyze settings={settings} onDone={onDone} report={report} />}
          {page === 'history' && <History history={history} go={go} openReport={openReport} />}
          {page === 'reviews' && <Reviews />}
          {page === 'settings' && <Settings settings={settings} setSettings={setSettings} clearHistory={clearHistory} />}
        </div>
      </main>
    </div>
  );
}
