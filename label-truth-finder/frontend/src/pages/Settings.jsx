import { useState } from 'react';
import { Card, Notice } from '../components/ui.jsx';
import { USE_MOCK } from '../services/api';

export const COUNTRIES = ['India', 'United States', 'European Union', 'United Kingdom', 'Canada', 'Australia'];

export default function Settings({ settings, setSettings, clearHistory }) {
  const [confirm, setConfirm] = useState(false);
  return (
    <>
      <Card>
        <h3>Preferences</h3>
        <div className="fields one">
          <label>Country / jurisdiction<select value={settings.country} onChange={(e) => setSettings({ ...settings, country: e.target.value })}>{COUNTRIES.map((c) => <option key={c}>{c}</option>)}</select></label>
          <label>Preferred product category<select value={settings.category} onChange={(e) => setSettings({ ...settings, category: e.target.value })}>{['', 'Food', 'Beverage', 'Skincare', 'Cosmetics', 'Other'].map((c) => <option key={c} value={c}>{c || 'No preference'}</option>)}</select></label>
        </div>
      </Card>
      <Card>
        <h3>Privacy</h3>
        <p className="muted">{USE_MOCK
          ? 'Demo mode: settings and history are saved only in this browser (localStorage) and the app shows demonstration data.'
          : 'No account is needed. Your country and category preferences are saved in this browser. Analysis history is saved in a database file on the computer running the backend. Label photos are sent only to the backend and AI model on your own computer, processed in memory and not stored. Product-name and barcode lookups send that text to Open Food Facts.'}</p>
        {!confirm ? <button className="btn" onClick={() => setConfirm(true)}>Clear history</button> : (
          <Notice tone="warn"><p>Delete all saved analyses? This cannot be undone.</p>
            <div className="actions"><button className="btn danger" onClick={() => { clearHistory(); setConfirm(false); }}>Yes, clear history</button><button className="btn" onClick={() => setConfirm(false)}>Cancel</button></div></Notice>
        )}
      </Card>
    </>
  );
}
