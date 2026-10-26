import { useRef, useState } from 'react';
import { UploadCloud, X, Loader2 } from 'lucide-react';
import { Card, Notice } from '../components/ui.jsx';
import Report from '../components/Report.jsx';
import { analyzeLabel } from '../services/api';

const TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_MB = 10;
const CATS = ['', 'Food', 'Beverage', 'Skincare', 'Cosmetics', 'Other'];

export default function Analyze({ settings, onDone, report }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [name, setName] = useState('');
  const [barcode, setBarcode] = useState('');
  const [category, setCategory] = useState(settings.category || '');
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState('');
  const [drag, setDrag] = useState(false);
  const input = useRef();

  const pick = (f) => {
    if (!f) return;
    if (!TYPES.includes(f.type)) return setErrors((e) => ({ ...e, file: 'Use a JPG, JPEG, PNG or WEBP image.' }));
    if (f.size > MAX_MB * 1048576) return setErrors((e) => ({ ...e, file: `Image must be under ${MAX_MB} MB.` }));
    if (preview) URL.revokeObjectURL(preview);
    setFile(f); setPreview(URL.createObjectURL(f)); setErrors((e) => ({ ...e, file: undefined, form: undefined }));
  };
  const remove = () => { if (preview) URL.revokeObjectURL(preview); setFile(null); setPreview(null); if (input.current) input.current.value = ''; };

  const submit = async (e) => {
    e.preventDefault();
    const err = {};
    if (!file && !name.trim() && !barcode.trim()) err.form = 'Add a label photo, a product name, or a barcode.';
    if (barcode && !/^\d{8,14}$/.test(barcode.trim())) err.barcode = 'Barcode must be 8–14 digits.';
    setErrors(err); setApiError('');
    if (Object.keys(err).length) return;
    setLoading(true);
    try {
      const data = await analyzeLabel(file, name.trim(), barcode.trim(), category, settings.country);
      onDone(data, preview);
    } catch (ex) {
      setApiError(`Analysis failed: ${ex.message}. Check that the backend is running and try again.`);
    } finally { setLoading(false); }
  };

  return (
    <>
      <Notice>Label analysis can contain errors. Always verify important health and regulatory information against the package and official sources.</Notice>
      <Card>
        <form onSubmit={submit} noValidate>
          {!preview ? (
            <div className={`drop ${drag ? 'drag' : ''}`} onClick={() => input.current.click()} onKeyDown={(e) => e.key === 'Enter' && input.current.click()} tabIndex={0} role="button"
              onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); }}>
              <UploadCloud size={36} /><strong>Drag a label photo here, or click to browse</strong>
              <span className="muted">Ingredients, nutrition panel, allergen statement or packaging · JPG, PNG, WEBP</span>
            </div>
          ) : (
            <div className="preview"><img src={preview} alt="Selected label preview" />
              <div className="actions"><button type="button" className="btn" onClick={() => input.current.click()}>Replace</button><button type="button" className="btn" onClick={remove}><X size={14} /> Remove</button></div></div>
          )}
          <input ref={input} type="file" hidden accept=".jpg,.jpeg,.png,.webp" onChange={(e) => pick(e.target.files[0])} />
          {errors.file && <p className="err">{errors.file}</p>}
          <div className="fields">
            <label>Product name<input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Oat cookies" /></label>
            <label>Barcode<input value={barcode} inputMode="numeric" onChange={(e) => setBarcode(e.target.value)} placeholder="8–14 digits" />{errors.barcode && <span className="err">{errors.barcode}</span>}</label>
            <label>Category (optional)<select value={category} onChange={(e) => setCategory(e.target.value)}>{CATS.map((c) => <option key={c} value={c}>{c || 'Select…'}</option>)}</select></label>
          </div>
          {errors.form && <p className="err">{errors.form}</p>}
          {apiError && <Notice tone="error">{apiError}</Notice>}
          <button className="btn primary" disabled={loading}>{loading ? <><Loader2 size={16} className="spin" /> Analyzing…</> : 'Analyze product'}</button>
        </form>
      </Card>
      {report && <Report data={report} country={settings.country} />}
    </>
  );
}
