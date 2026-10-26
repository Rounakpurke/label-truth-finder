// Single place for all backend communication.
// Backend URL and demo mode are configurable (see .env.example):
//   VITE_API_BASE_URL (default http://127.0.0.1:5001)   VITE_USE_MOCK=true for demo data only
import { mockAnalysis, mockHistory, mockReviews } from '../mock/mockData';

export const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5001').replace(/\/$/, '');
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
const delay = (ms) => new Promise((r) => setTimeout(r, ms));

async function request(path, options) {
  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, options);
  } catch {
    throw new Error(`Cannot reach the backend at ${BASE_URL}. Is it running?`);
  }
  let body = null;
  try { body = await res.json(); } catch { /* non-JSON response */ }
  if (!res.ok) throw new Error(body?.error?.message || `Server responded with ${res.status}`);
  return body;
}

export async function analyzeLabel(imageFile, productName, barcode, category, country) {
  if (USE_MOCK) {
    await delay(1200);
    return { ...mockAnalysis, product_name: productName || mockAnalysis.product_name, barcode: barcode || null, category: category || mockAnalysis.category };
  }
  const form = new FormData();
  if (imageFile) form.append('image', imageFile); // backend field name: "image"
  form.append('product_name', productName || '');
  form.append('barcode', barcode || '');
  form.append('category', category || '');
  form.append('country', country || 'India');
  return request('/api/analyze', { method: 'POST', body: form }); // browser sets the multipart Content-Type
}

export async function searchProduct(query) {
  if (USE_MOCK) { await delay(500); return [{ id: 'demo', product_name: mockAnalysis.product_name, brand: mockAnalysis.brand, demo: true }]; }
  return request(`/api/products/search?q=${encodeURIComponent(query)}`);
}

export async function getAnalysisHistory() {
  if (USE_MOCK) { await delay(200); return mockHistory; }
  return request('/api/history');
}

export async function clearAnalysisHistory() {
  if (USE_MOCK) return { deleted: 0 };
  return request('/api/history', { method: 'DELETE' });
}

// productId 'all' returns every review (used by the Reviews page)
export async function getProductReviews(productId) {
  if (USE_MOCK) { await delay(200); return mockReviews; }
  return request(`/api/products/${encodeURIComponent(productId)}/reviews`);
}

export async function submitProductReview(reviewData) {
  if (USE_MOCK) { await delay(300); return { ...reviewData, id: `local-${Date.now()}`, helpful: 0, demo: true }; }
  return request('/api/reviews', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(reviewData) });
}

export async function markReviewHelpful(reviewId) {
  if (USE_MOCK) return null; // handled locally by the caller
  return request(`/api/reviews/${encodeURIComponent(reviewId)}/helpful`, { method: 'POST' });
}
