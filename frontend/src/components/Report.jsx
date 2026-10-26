import { useState } from 'react';
import { ChevronDown, ExternalLink } from 'lucide-react';
import { Card, Notice, DemoBadge, none } from './ui.jsx';

const arr = (v) => (Array.isArray(v) ? v : []);
const NUTRI = [['energy', 'Calories / energy'], ['protein', 'Protein'], ['carbohydrates', 'Total carbohydrates'], ['sugars', 'Total sugars'], ['added_sugars', 'Added sugars'], ['fat', 'Total fat'], ['saturated_fat', 'Saturated fat'], ['trans_fat', 'Trans fat'], ['fibre', 'Dietary fibre'], ['sodium', 'Sodium / salt']];
const STATUS = { confirmed: 'Confirmed restriction', none_found: 'No restriction found in checked sources', not_verified: 'Not verified' };
const TABS = ['Overview', 'Grade', 'Daily Allowance', 'Alternatives', 'Detailed Analysis', 'Ingredients', 'Allergens', 'Nutrition', 'Sugars', 'Concerns', 'Regulations', 'Notes', 'Uncertainty', 'Sources'];

const List = ({ items, empty }) => (arr(items).length ? <ul className="list">{items.map((x, i) => <li key={i}>{typeof x === 'string' ? x : JSON.stringify(x)}</li>)}</ul> : <p className="muted">{empty}</p>);

function Ingredient({ item }) {
  const [open, setOpen] = useState(false);
  const fromPackage = item.source_status === 'package';
  const badge = { package: 'Name read from package', database: 'Name from online database' }[item.source_status] || 'General explanation';
  return (
    <div className="row">
      <button className="row-head" aria-expanded={open} onClick={() => setOpen(!open)}>
        <strong>{item.name}</strong><span className="muted">{none(item.type)}</span>
        <span className={`badge ${fromPackage ? 'ok' : ''}`}>{badge}</span>
        <ChevronDown size={16} className={open ? 'flip' : ''} />
      </button>
      {open && <div className="row-body"><p><b>Typical purpose:</b> {none(item.purpose)}</p><p>{none(item.explanation)}</p>{item.explanation && <p className="muted">Explanation is general knowledge from an AI model, not text from the label.</p>}{item.uncertainty && <p className="muted">Uncertainty: {item.uncertainty}</p>}</div>}
    </div>
  );
}

export default function Report({ data, country }) {
  const [tab, setTab] = useState('Overview');
  if (!data) return null;
  const n = data.nutrition || {};
  const regs = arr(data.country_regulations).filter((r) => !r.country || r.country === country);
  const grade = data.grade || {};
  const insights = arr(data.detailed_insights);
  const daily = data.daily_guidance || {};
  const dailyRows = arr(daily.rows);
  const alternatives = arr(data.alternatives);
  const panels = {
    Grade: (
      <div className="grade-panel">
        <div className="report-head">
          <div><h3>Product grade: {none(grade.grade)}</h3><p className="muted">{grade.score == null ? 'No score assigned' : `${grade.score}/100`} · Confidence: {none(grade.confidence)}</p></div>
          <span className={`grade-mark ${['S', 'A'].includes(grade.grade) ? 'good' : ['C', 'D'].includes(grade.grade) ? 'caution' : ''}`}>{none(grade.grade)}</span>
        </div>
        <p>{none(grade.basis)}</p>
        <h4>Why this grade?</h4>
        <List items={grade.reasons} empty="No grading reasons are available." />
        <h4>Important limitations</h4>
        <List items={grade.limitations} empty="No additional limitations provided." />
      </div>
    ),
    'Daily Allowance': (
      <div>
        <p><b>{none(daily.population || 'General adult reference only')}</b></p>
        <p className="muted">Product nutrition basis: {none(daily.basis || n.basis)}. The figures below are broad daily references, not personalized targets.</p>
        {dailyRows.length ? <table className="table"><thead><tr><th>Nutrient</th><th>Product label</th><th>General daily reference</th><th>How to interpret</th></tr></thead><tbody>{dailyRows.map((r, i) => <tr key={i}><th scope="row">{r.nutrient}</th><td>{none(r.product_value)}</td><td>{r.daily_reference}</td><td>{r.context}</td></tr>)}</tbody></table> : <p className="muted">Daily reference guidance is not available for this report.</p>}
        <List items={daily.notes} empty="Daily guidance notes are unavailable." />
        <Notice>These are broad adult references, not a personal diet plan. A product value per 100 g/ml is not the same as your intake for the day. Total sugars on a label are not directly interchangeable with WHO's free-sugar limit.</Notice>
      </div>
    ),
    Alternatives: (
      <div>
        <p>Ideas to compare or swap—not endorsements. Check the full label, serving size, allergies, preferences, and availability.</p>
        {alternatives.length ? alternatives.map((item, i) => <div className="row pad" key={i}><strong>{item.title}</strong><p>{item.suggestion}</p><p className="muted">Why consider it: {item.reason}</p></div>) : <p className="muted">No alternative suggestions were returned.</p>}
        <Notice>These suggestions are general. Choose alternatives that fit your needs, culture, budget, and any allergies or medical dietary advice.</Notice>
      </div>
    ),
    'Detailed Analysis': (
      <div>
        {insights.length ? insights.map((item, i) => (
          <div className="row pad" key={i}><strong>{item.title}</strong><p>{item.detail}</p></div>
        )) : <p className="muted">Detailed observations are not available for this report.</p>}
        <Notice>These observations summarize the available label and database information. They are not medical advice and do not prove that a product is healthy, unhealthy, safe, unsafe, approved or illegal.</Notice>
      </div>
    ),
    Overview: (
      <dl className="dl">
        {[['Product name', data.product_name], ['Brand', data.brand], ['Category', data.category], ['Barcode', data.barcode], ['Data source', data.data_source], ['Last updated', data.last_updated]].map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{none(v)}</dd></div>)}
        <div><dt>Product image</dt><dd>{data.image_url ? <img className="thumb" src={data.image_url} alt="" /> : 'Not available'}</dd></div>
      </dl>
    ),
    Ingredients: (
      <>
        {data.ingredients_text && <p><b>Ingredient text from the package:</b> {data.ingredients_text}</p>}
        {arr(data.ingredient_analysis).length ? arr(data.ingredient_analysis).map((it, i) => <Ingredient key={i} item={it} />) : <List items={data.ingredients} empty="No ingredients were returned." />}
      </>
    ),
    Allergens: (
      <>
        <Notice tone="warn">This list may be incomplete. People with serious allergies must check the original package.</Notice>
        <h4>Declared on the package</h4><List items={data.declared_allergens} empty="No allergen statement was read. This does not mean the product is allergen-free." />
        <h4>Possible matches in the ingredient text</h4>
        <List items={arr(data.possible_allergen_matches).map((m) => (typeof m === 'string' ? m : `${m.allergen}${m.matched_text ? ` (matched “${m.matched_text}”)` : ''}`))} empty="No possible matches returned." />
        <h4>Could not be verified</h4><List items={data.not_determined} empty="Nothing listed." />
      </>
    ),
    Nutrition: (
      <>
        <p className="muted">Basis: {none(n.basis)}</p>
        <table className="table"><tbody>{NUTRI.map(([k, label]) => <tr key={k}><th scope="row">{label}</th><td>{none(n[k])}</td></tr>)}</tbody></table>
      </>
    ),
    Sugars: (
      <>
        {arr(data.sugar_sources).length ? arr(data.sugar_sources).map((s, i) => <div className="row pad" key={i}><strong>{s.name}</strong><p>{none(s.role)}</p></div>) : <p className="muted">No sugars or sweeteners found in the ingredient list.</p>}
        <p className="muted">Presence of an ingredient alone does not make it harmful. Total sugars: {none(n.sugars)}.</p>
      </>
    ),
    Concerns: arr(data.possible_concerns).length ? arr(data.possible_concerns).map((c, i) => <div className="row pad" key={i}><strong>{c.point}</strong><p>{none(c.reason)}</p><p className="muted">Source: {none(c.source)}</p></div>) : <p className="muted">No points to review were returned.</p>,
    Regulations: (
      <>
        <Notice>“No restriction found” does not prove a product is legally approved. Check official sources.</Notice>
        {regs.length ? regs.map((r, i) => (
          <div className="row pad" key={i}>
            <strong>{r.country || country} · {none(r.subject)}</strong>
            <p><span className={`badge ${r.status === 'confirmed' ? 'bad' : ''}`}>{STATUS[r.status] || 'Not verified'}</span></p>
            <p>{none(r.explanation)}</p>
            <p className="muted">{r.source_url ? <a href={r.source_url} target="_blank" rel="noreferrer">{r.source_name || 'Official source'} <ExternalLink size={12} /></a> : `Source: ${none(r.source_name)}`} · Date: {none(r.date)}</p>
          </div>
        )) : <p><span className="badge">Not verified</span> No verified result for {country}.</p>}
      </>
    ),
    Notes: <List items={data.positive_notes} empty="No observations available." />,
    Uncertainty: (<><h4>Unreadable or uncertain text</h4><List items={data.uncertain_text} empty="Nothing flagged." /><h4>Not determined</h4><List items={data.not_determined} empty="Nothing flagged." />
      {arr(data.discrepancies).length > 0 && <><h4>Package vs online record differences</h4><List items={data.discrepancies} empty="" /></>}</>),
    Sources: arr(data.sources).length ? arr(data.sources).map((s, i) => <div className="row pad" key={i}><strong>{s.url ? <a href={s.url} target="_blank" rel="noreferrer">{s.name} <ExternalLink size={12} /></a> : s.name}</strong><p className="muted">Retrieved: {none(s.retrieved)}</p></div>) : <p className="muted">No sources were returned.</p>,
  };
  return (
    <Card>
      <div className="report-head"><h2>{none(data.product_name)}</h2>{data.demo && <DemoBadge />}</div>
      <div className="tabs" role="tablist">{TABS.map((t) => <button key={t} role="tab" aria-selected={tab === t} className={tab === t ? 'on' : ''} onClick={() => setTab(t)}>{t}</button>)}</div>
      <div className="panel" role="tabpanel">{panels[tab]}</div>
    </Card>
  );
}
