import { History as H } from 'lucide-react';
import { Card, Empty, DemoBadge } from '../components/ui.jsx';

export default function History({ history, openReport, go }) {
  if (!history.length) return <Card><Empty icon={H} title="No analyses yet" text="Analyze a product and it will show up here." action={<button className="btn primary" onClick={() => go('analyze')}>Analyze a product</button>} /></Card>;
  return (
    <Card>
      {history.map((h) => (
        <div className="row pad between" key={h.id}>
          <span className="flex">{h.thumbnail ? <img className="thumb sm" src={h.thumbnail} alt="" /> : <span className="thumb sm ph" />}
            <span>{h.product_name} {h.demo && <DemoBadge />}<br /><small className="muted">{h.date} · {h.status}</small></span></span>
          <button className="btn" onClick={() => openReport(h)}>Open report</button>
        </div>
      ))}
    </Card>
  );
}
