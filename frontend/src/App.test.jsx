import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import App from './App.jsx';

const traits = {
  groups: {
    image_quality: ['resolution', 'blur'],
    slant_and_baseline: ['dominant_slant', 'baseline_stability'],
    stroke: ['pressure_estimate'],
  },
  disclaimer: 'Handwriting is not validated personality science.',
};

const mockAnalysis = {
  product_name: 'InkPersona',
  document_type: 'mock scanned page',
  objective_traits: {
    image_quality: {
      resolution: { value: 'full HD', confidence: 'high', evidence: 'Visible scan.' },
    },
    stroke: {
      pressure_estimate: { value: 'not reliably detectable', confidence: 'low', evidence: 'Flat scan.' },
    },
  },
  interpretation: {
    style_summary: 'Controlled but cautious style impression.',
    possible_impressions: ['may appear organized'],
    alternative_explanations: ['pen type'],
  },
  safety_review: {
    required_disclaimer: 'Handwriting alone is not a validated way to determine personality.',
  },
};

beforeEach(() => {
  global.fetch = vi.fn((url) => {
    if (String(url).endsWith('/traits')) return Promise.resolve({ ok: true, json: () => Promise.resolve(traits) });
    if (String(url).endsWith('/mock-analysis')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAnalysis) });
    return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: 'unexpected' }) });
  });
  global.URL.createObjectURL = vi.fn(() => 'blob:preview');
  global.URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('InkPersona app', () => {
  test('renders safety-first positioning and objective trait count', async () => {
    render(<App />);
    expect(screen.getByText(/Handwriting style analysis without fake certainty/i)).toBeInTheDocument();
    expect(screen.getByText(/No clinical claims/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/5 objective traits/i)).toBeInTheDocument());
  });

  test('loads demo report and shows disclaimer', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('button', { name: /Use demo result/i }));
    expect(await screen.findByText(/mock scanned page/i)).toBeInTheDocument();
    expect(screen.getByText(/Controlled but cautious/i)).toBeInTheDocument();
    expect(screen.getAllByText(/not a validated way/i).length).toBeGreaterThan(0);
  });
});
