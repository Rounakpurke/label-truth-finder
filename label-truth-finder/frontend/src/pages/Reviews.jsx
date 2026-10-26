import { useEffect, useState } from 'react';
import { Star, ThumbsUp, MessageSquare } from 'lucide-react';
import { Card, Notice, Empty, DemoBadge } from '../components/ui.jsx';
import { USE_MOCK, getProductReviews, submitProductReview, markReviewHelpful } from '../services/api';

const blank = { product: '', brand: '', rating: 0, text: '', user: '' };

export default function Reviews() {
  const [reviews, setReviews] = useState([]);
  const [q, setQ] = useState('');
  const [f, setF] = useState(blank);
  const [err, setErr] = useState({});
  const [loadError, setLoadError] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [saving, setSaving] = useState(false);
  useEffect(() => { getProductReviews('all').then(setReviews).catch((e) => setLoadError(`Could not load reviews: ${e.message}`)); }, []);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    const x = {};
    if (!f.product.trim()) x.product = 'Enter the product name.';
    if (!f.rating) x.rating = 'Choose a rating from 1 to 5.';
    if (f.text.trim().length < 10) x.text = 'Write at least 10 characters.';
    setErr(x);
    if (Object.keys(x).length) return;
    if (saving) return; // ignore accidental double clicks
    setSaving(true); setSubmitError('');
    try {
      const saved = await submitProductReview({ ...f, user: f.user.trim() || 'anonymous', date: new Date().toISOString().slice(0, 10) });
      setReviews((prev) => [saved, ...prev.filter((x) => x.id !== saved.id)]); setF(blank);
    } catch (ex) { setSubmitError(`Could not save the review: ${ex.message}`); }
    finally { setSaving(false); }
  };
  const helpful = async (r) => {
    try {
      const updated = USE_MOCK ? { ...r, helpful: r.helpful + 1 } : await markReviewHelpful(r.id);
      setReviews((prev) => prev.map((x) => (x.id === r.id ? { ...x, helpful: updated.helpful } : x)));
    } catch (ex) { setSubmitError(`Could not record your vote: ${ex.message}`); }
  };
  const shown = reviews.filter((r) => `${r.product} ${r.brand}`.toLowerCase().includes(q.toLowerCase()));

  return (
    <>
      <Notice>Reviews are personal opinions, not verified medical or scientific evidence. {USE_MOCK ? 'In demo mode, reviews exist only in this browser session.' : 'Reviews are saved in a local database on the computer running the backend. Usernames are not verified, and this local prototype has no abuse protection, so it is not suitable for public deployment as it is.'}</Notice>
      {loadError && <Notice tone="error">{loadError} Check that the backend is running.</Notice>}
      {submitError && <Notice tone="error">{submitError}</Notice>}
      <div className="cols">
        <Card>
          <input className="search" placeholder="Search by product or brand" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search reviews" />
          {shown.length ? shown.map((r) => (
            <div className="row pad" key={r.id}>
              <strong>{r.product}</strong> <span className="muted">{r.brand}</span> {r.demo && <DemoBadge />}
              <div className="stars" aria-label={`${r.rating} out of 5`}>{'★'.repeat(r.rating)}{'☆'.repeat(5 - r.rating)} <span className="muted">{r.rating}/5</span></div>
              <p>{r.text}</p>
              <small className="muted">{r.user} · {r.date}</small>{' '}
              <button className="btn sm" onClick={() => helpful(r)}><ThumbsUp size={12} /> Helpful ({r.helpful})</button>
            </div>
          )) : <Empty icon={MessageSquare} title="No reviews found" text="Try a different search or write the first review." />}
        </Card>
        <Card>
          <h3>Write a review</h3>
          <form onSubmit={submit} noValidate className="fields one">
            <label>Product name<input value={f.product} onChange={set('product')} />{err.product && <span className="err">{err.product}</span>}</label>
            <label>Brand<input value={f.brand} onChange={set('brand')} /></label>
            <div><span className="lbl">Rating</span><div className="rate">{[1, 2, 3, 4, 5].map((n) => <button type="button" key={n} aria-label={`${n} stars`} onClick={() => setF({ ...f, rating: n })}><Star size={22} fill={n <= f.rating ? 'currentColor' : 'none'} /></button>)}</div>{err.rating && <span className="err">{err.rating}</span>}</div>
            <label>Review<textarea rows={4} value={f.text} onChange={set('text')} />{err.text && <span className="err">{err.text}</span>}</label>
            <label>Username (optional)<input value={f.user} onChange={set('user')} /></label>
            <button className="btn primary" disabled={saving}>{saving ? 'Saving…' : 'Submit review'}</button>
          </form>
        </Card>
      </div>
    </>
  );
}
