import { Info, AlertTriangle } from 'lucide-react';
export const Card = ({ children, className = '' }) => <section className={`card ${className}`}>{children}</section>;
export const Notice = ({ tone = 'info', children }) => (
  <div className={`notice ${tone}`} role={tone === 'error' ? 'alert' : 'note'}>
    {tone === 'info' ? <Info size={18} /> : <AlertTriangle size={18} />}<div>{children}</div>
  </div>
);
export const Empty = ({ icon: Icon, title, text, action }) => (
  <div className="empty">{Icon && <Icon size={32} />}<h3>{title}</h3><p>{text}</p>{action}</div>
);
export const DemoBadge = () => <span className="badge demo">Demo data</span>;
export const none = (v) => (v === null || v === undefined || v === '' ? 'Not available' : v);
