// ALL MOCK DATA LIVES HERE. Everything is clearly marked as demonstration data.
export const DEMO_NOTICE = 'Demonstration data – not a real analysis.';

export const mockAnalysis = {
  demo: true,
  product_name: 'Demo Oat Cookies',
  brand: 'Demo Brand',
  category: 'Food',
  barcode: null,
  image_url: null,
  data_source: 'Demonstration data',
  last_updated: null,
  ingredients_text: 'Wheat flour, sugar, palm oil, oats, milk solids, salt, raising agent (500)',
  ingredients: ['Wheat flour', 'Sugar', 'Palm oil', 'Oats', 'Milk solids', 'Salt', 'Raising agent (500)'],
  ingredient_analysis: [
    { name: 'Wheat flour', type: 'Cereal', purpose: 'Structure / bulk', explanation: 'Ground wheat grain, the main base of baked goods.', source_status: 'general' },
    { name: 'Sugar', type: 'Sweetener', purpose: 'Sweetness, browning', explanation: 'Table sugar (sucrose).', source_status: 'general' },
    { name: 'Raising agent (500)', type: 'Additive', purpose: 'Helps dough rise', explanation: 'INS 500 refers to sodium carbonates.', source_status: 'package' },
  ],
  nutrition_text: null,
  nutrition: {
    basis: 'per 100 g',
    energy: '480 kcal', protein: '7 g', carbohydrates: '66 g', sugars: '22 g', added_sugars: null,
    fat: '20 g', saturated_fat: '9 g', trans_fat: null, fibre: '3 g', sodium: '310 mg',
  },
  sugar_sources: [{ name: 'Sugar', role: 'Adds sweetness and helps browning.' }],
  declared_allergens: ['Wheat (gluten)', 'Milk'],
  possible_allergen_matches: [{ allergen: 'Oats (gluten cross-contact possible)', matched_text: 'oats' }],
  possible_concerns: [
    { point: 'Declared allergens present', reason: 'The package declares wheat and milk.', source: 'Package label' },
  ],
  positive_notes: ['Nutrition information is clearly provided', 'Allergen declaration is visible'],
  country_regulations: [
    { country: 'India', subject: 'Raising agent (500)', status: 'not_verified', explanation: 'No verified regulatory data was returned for this item.', source_name: null, source_url: null, date: null },
  ],
  sources: [{ name: 'Demonstration data', url: null, retrieved: null }],
  uncertain_text: ['Part of the ingredient line was cropped in the demo image.'],
  not_determined: ['Added sugars are not declared.', 'Trans fat is not declared.'],
};

export const mockHistory = [
  { id: 'demo-1', product_name: 'Demo Oat Cookies', thumbnail: null, date: '2026-10-20', status: 'Completed', demo: true, report: mockAnalysis },
];

export const mockReviews = [
  { id: 'r1', product: 'Demo Oat Cookies', brand: 'Demo Brand', rating: 4, text: 'Tasty, a bit sweet for me.', user: 'demo_user', date: '2026-10-10', helpful: 2, demo: true },
];
