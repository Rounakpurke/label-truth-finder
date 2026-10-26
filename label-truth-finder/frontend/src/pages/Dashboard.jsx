import { Upload, Search, FlaskConical, ShieldAlert, Apple, Globe, History } from 'lucide-react';
import { Card, Empty, DemoBadge } from '../components/ui.jsx';

const FEATURES = [[FlaskConical, 'Ingredient Analysis', 'Plain-language explanations of each ingredient.'], [ShieldAlert, 'Allergen Detection', 'Declared and possible allergen matches.'], [Apple, 'Nutrition Facts', 'Values exactly as printed on the label.'], [Globe, 'Country Regulations', 'Restrictions with official source links.']];

export default function Dashboard({ history, go, openReport }) {
  return (
    <>
      <Card className="hero">
        <h2>Understand what’s inside your products.</h2>
        <p>Upload a label photo or look up a product by barcode or name.</p>
        <div className="actions">
          <button className="btn primary" onClick={() => go('analyze')}><Upload size={16} /> Upload label photo</button>
          <button className="btn" onClick={() => go('analyze')}><Search size={16} /> Enter barcode / product name</button>
        </div>
      </Card>
      <div className="grid4">{FEATURES.map(([I, t, d]) => <Card key={t}><I size={20} className="accent" /><h3>{t}</h3><p className="muted">{d}</p></Card>)}</div>
      <Card>
        <h3>Recent analyses</h3>
        {history.length ? history.slice(0, 3).map((h) => (
          <div className="row pad between" key={h.id}><span>{h.product_name} {h.demo && <DemoBadge />}<br /><small className="muted">{h.date}</small></span><button className="btn" onClick={() => openReport(h)}>Open report</button></div>
        )) : <Empty icon={History} title="No analyses yet" text="Your analyzed products will appear here." action={<button className="btn primary" onClick={() => go('analyze')}>Analyze a product</button>} />}
      </Card>
    </>
  );
}
