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
  grade: {
    grade: 'A', score: 78, confidence: 'high',
    basis: 'Illustrative rule-based score from available per-100 g/ml nutrition values; not an official standard.',
    reasons: ['Elevated total sugars: 22 g per 100 g/ml (−15 points).', 'Elevated saturated fat: 9 g per 100 g/ml (−12 points).', 'Sodium: 310 mg per 100 g/ml (−5 points).', 'Fibre is 3 g per 100 g/ml (+5 points).', 'Protein is 7 g per 100 g/ml (+5 points).'],
    limitations: ['This is demonstration data and an educational heuristic, not an official government, medical or dietetic rating.', 'Missing nutrients are unknown, not zero.', 'Ingredient order and allergen warnings are reported separately.'],
  },
  daily_guidance: {
    basis: 'per 100 g',
    population: 'General adult reference only',
    rows: [
      { nutrient: 'Energy', product_value: '480 kcal', daily_reference: 'About 2,000 kcal/day for a general adult reference', context: 'Energy needs vary by person.' },
      { nutrient: 'Sodium', product_value: '310 mg', daily_reference: 'Less than 2,000 mg/day for adults (WHO guidance)', context: 'This product lists 310 mg per 100 g.' },
      { nutrient: 'Saturated fat', product_value: '9 g', daily_reference: 'Keep below about 22 g/day on a 2,000 kcal diet', context: 'This product lists 9 g per 100 g.' },
      { nutrient: 'Fibre', product_value: '3 g', daily_reference: 'About 25 g/day as a broad adult reference', context: 'This product lists 3 g per 100 g.' },
      { nutrient: 'Protein', product_value: '7 g', daily_reference: '50 g/day is a rough label-reference value, not a personal target', context: 'Needs vary by person.' },
      { nutrient: 'Sugars', product_value: '22 g', daily_reference: 'WHO: free sugars below 50 g/day, ideally below 25 g/day on a 2,000 kcal diet', context: 'Total sugars can include naturally occurring sugars and cannot be directly equated with free sugars.' },
    ],
    notes: ['Product amounts are shown per 100 g, not a recommended serving size.', 'Personal needs vary; ask a qualified professional for individualized targets.'],
  },
  alternatives: [
    { title: 'For sweet snacks', suggestion: 'Compare with fresh whole fruit, plain unsweetened yoghurt/curd, or a smaller portion of the treat.', reason: 'These can help vary snacks and may reduce added/free sugar depending on the choice.' },
    { title: 'Lower-sugar option', suggestion: 'Look for an unsweetened/plain version or a similar product with lower added sugar per 100 g and per serving.', reason: 'This demo label lists 22 g total sugars per 100 g; total sugars are not the same as free sugars.' },
    { title: 'Lower saturated-fat option', suggestion: 'Compare similar products for lower saturated fat.', reason: 'This demo label lists 9 g saturated fat per 100 g.' },
  ],
  detailed_insights: [
    { title: 'Nutrition basis', detail: 'Values are reported per 100 g. Compare like-for-like serving bases.' },
    { title: 'Ingredient list', detail: 'Seven ingredient entries are shown in this demonstration. Ingredients are generally listed in descending order by weight, but exact amounts are not shown.' },
    { title: 'Total sugars', detail: 'Label value: 22 g. Interpretation depends on serving size and overall diet.' },
    { title: 'Saturated fat', detail: 'Label value: 9 g. This is descriptive and not medical advice.' },
  ],
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
