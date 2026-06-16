import React, { useEffect, useMemo, useState } from 'react';
import { Brain, FileImage, ShieldCheck, Sparkles, UploadCloud } from 'lucide-react';
import { analyzeImage, fetchMockAnalysis, fetchTraits } from './api.js';
import './styles.css';

const DISCLAIMER = 'Handwriting alone is not a validated way to determine personality, mental health, hiring fitness, intelligence, or honesty. InkPersona is for reflection and entertainment.';

function flattenTraits(groups) {
  if (!groups) return [];
  return Object.entries(groups).flatMap(([group, names]) => names.map((name) => ({ group, name })));
}

function TraitCard({ label, observation }) {
  return (
    <article className="trait-card">
      <div>
        <span className="trait-label">{label.replaceAll('_', ' ')}</span>
        <strong>{observation?.value || 'Not assessed'}</strong>
      </div>
      <span className={`confidence confidence-${observation?.confidence || 'low'}`}>{observation?.confidence || 'low'}</span>
      <p>{observation?.evidence || 'No visible evidence available.'}</p>
    </article>
  );
}

function Report({ result }) {
  if (!result) return null;
  const groups = result.objective_traits || {};
  return (
    <section className="report" aria-label="InkPersona analysis report">
      <div className="report-hero">
        <p className="eyebrow">Analysis report</p>
        <h2>{result.document_type}</h2>
        <p>{result.interpretation?.style_summary}</p>
      </div>

      <div className="interpretation-grid">
        <div className="panel">
          <h3>Possible impressions</h3>
          <ul>{(result.interpretation?.possible_impressions || []).map((item) => <li key={item}>{item}</li>)}</ul>
        </div>
        <div className="panel caution">
          <h3>Safety limits</h3>
          <p>{result.safety_review?.required_disclaimer || DISCLAIMER}</p>
        </div>
        <div className="panel">
          <h3>Alternative explanations</h3>
          <ul>{(result.interpretation?.alternative_explanations || []).map((item) => <li key={item}>{item}</li>)}</ul>
        </div>
      </div>

      {Object.entries(groups).map(([groupName, observations]) => (
        <section className="trait-section" key={groupName}>
          <h3>{groupName.replaceAll('_', ' ')}</h3>
          <div className="trait-grid">
            {Object.entries(observations).map(([name, observation]) => (
              <TraitCard key={name} label={name} observation={observation} />
            ))}
          </div>
        </section>
      ))}
    </section>
  );
}

export default function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState('');
  const [traits, setTraits] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const objectiveTraitCount = useMemo(() => flattenTraits(traits?.groups).length, [traits]);

  useEffect(() => {
    fetchTraits().then(setTraits).catch(() => setTraits({ groups: {} }));
  }, []);

  function onFileChange(event) {
    const nextFile = event.target.files?.[0];
    setFile(nextFile || null);
    setResult(null);
    setError('');
    if (preview) URL.revokeObjectURL(preview);
    setPreview(nextFile ? URL.createObjectURL(nextFile) : '');
  }

  async function runAnalysis(useMock = false) {
    setLoading(true);
    setError('');
    try {
      const nextResult = useMock ? await fetchMockAnalysis() : await analyzeImage(file);
      setResult(nextResult);
    } catch (err) {
      setError(err.message || 'Analysis failed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <p className="eyebrow"><Sparkles size={16} /> InkPersona</p>
          <h1>Handwriting style analysis without fake certainty.</h1>
          <p className="hero-copy">Upload a full-HD scanned handwritten document. InkPersona extracts objective handwriting traits, then gives cautious self-reflection impressions with clear scientific limits.</p>
          <div className="hero-badges">
            <span><ShieldCheck size={16} /> No clinical claims</span>
            <span><Brain size={16} /> OpenAI vision-ready</span>
            <span><FileImage size={16} /> {objectiveTraitCount || '60+'} objective traits</span>
          </div>
        </div>
        <aside className="disclaimer-card">
          <h2>Important boundary</h2>
          <p>{DISCLAIMER}</p>
        </aside>
      </section>

      <section className="upload-panel">
        <label className="dropzone">
          <UploadCloud size={34} />
          <span>{file ? file.name : 'Upload JPEG, PNG, or WEBP scan'}</span>
          <small>Best input: clean, uncropped, full-page scan at 1080p or higher.</small>
          <input type="file" accept="image/png,image/jpeg,image/webp" onChange={onFileChange} />
        </label>
        {preview && <img className="preview" src={preview} alt="Uploaded handwriting preview" />}
        <div className="actions">
          <button onClick={() => runAnalysis(false)} disabled={!file || loading}>{loading ? 'Analyzing...' : 'Analyze handwriting'}</button>
          <button className="secondary" onClick={() => runAnalysis(true)} disabled={loading}>Use demo result</button>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
      </section>

      <section className="registry-panel">
        <h2>Objective trait coverage</h2>
        <p>The app asks the vision model to cover every visible category below before writing any interpretation.</p>
        <div className="registry-grid">
          {Object.entries(traits?.groups || {}).map(([group, names]) => (
            <article key={group}>
              <strong>{group.replaceAll('_', ' ')}</strong>
              <span>{names.length} traits</span>
            </article>
          ))}
        </div>
      </section>

      <Report result={result} />
    </main>
  );
}
