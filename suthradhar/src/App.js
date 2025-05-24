// frontend/src/App.js
import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  // Input state
  const [url, setUrl] = useState('');
  const [fileText, setFileText] = useState('');
  const [angle, setAngle] = useState('');
  const [keywords, setKeywords] = useState('');
  const [citationStyle, setCitationStyle] = useState('APA','Bluebook');

  // Results state
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Handle file upload and read text
   */
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => setFileText(evt.target.result);
    reader.readAsText(file);
  };

  /**
   * Send data to backend for analysis
   */
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (url === '' && fileText === '') {
    setError('Please provide either a Paper URL or upload a PDF.');
    return;
  }
    
    setLoading(true);
    setError(null);

    const payload = {
      url: url || null,
      pdf_text: fileText || null,
      angle: angle,
      keywords: keywords ? keywords.split(',').map(k => k.trim()) : [],
      citation_style: citationStyle
    };

    try {
      const response = await axios.post('http://127.0.0.1:5000/api/analyze', payload);
      setResults(response.data.sources || []);
    } catch (err) {
      console.error('API error:', err);
      setError('Failed to fetch results. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Download the research brief as a text file
   */
  const downloadBrief = () => {
    let content = `Research Angle: ${angle}\n\n`;
    results.forEach((src, i) => {
      content += `${i + 1}. ${src.title} [Score: ${src.score.toFixed(2)}]\n`;
      content += `Summary: ${src.summary}\nCitation: ${src.citation}\n\n`;
    });

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'research_brief.txt';
    link.click();
  };

  return (
    <div className="App">
      <h1>AI Legal Research Companion</h1>
      <form onSubmit={handleSubmit}>
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <label>
          Paper URL:
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://..."
          />
        </label>

        <label>
          Or Upload PDF:
          <input
            type="file"
            accept="application/pdf"
            onChange={handleFileUpload}
          />
        </label>

        <label>
          New Research Angle:
          <input
            type="text"
            value={angle}
            onChange={(e) => setAngle(e.target.value)}
            placeholder="Enter your research angle"
            required
          />
        </label>

        <label>
          Optional Keywords (comma-separated):
          <input
            type="text"
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="e.g. data privacy, blockchain"
          />
        </label>

        <label>
          Citation Style:
          <select
            value={citationStyle}
            onChange={(e) => setCitationStyle(e.target.value)}
          >
            <option>APA</option>
            <option>Bluebook</option>
          </select>
        </label>

        <button id="analyze-btn" type="submit" disabled={loading}>
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
        <button
          id="download-btn"
          type="button"
          onClick={downloadBrief}
          disabled={!results.length}
        >
          Download Brief
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      <div className="results">
        {results.map((src, idx) => (
          <div key={idx} className="result-card">
            <h3>
              {src.title} <span>({src.year})</span>
            </h3>
            <div className="result-meta">
              <em>{src.authors}</em> &mdash; Relevance: {src.score.toFixed(2)}
            </div>
            <div className="result-summary">{src.summary}</div>
            <div className="result-citation">
              <strong>Citation:</strong> {src.citation}
            </div>
            <div className="result-link">
              <a href={src.link} target="_blank" rel="noopener noreferrer">
                View Source
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
