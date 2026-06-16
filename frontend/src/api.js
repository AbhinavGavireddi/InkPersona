const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const ENABLE_MOCK = import.meta.env.VITE_ENABLE_MOCK_ANALYSIS !== 'false';

export async function fetchTraits() {
  const response = await fetch(`${API_BASE_URL}/traits`);
  if (!response.ok) throw new Error('Could not load trait registry.');
  return response.json();
}

export async function fetchMockAnalysis() {
  const response = await fetch(`${API_BASE_URL}/mock-analysis`);
  if (!response.ok) throw new Error('Mock analysis failed.');
  return response.json();
}

export async function analyzeImage(file) {
  if (ENABLE_MOCK && !file) return fetchMockAnalysis();
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`${API_BASE_URL}/analyze`, { method: 'POST', body: formData });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || 'Analysis failed. Check API key and image quality.');
  }
  return body;
}
