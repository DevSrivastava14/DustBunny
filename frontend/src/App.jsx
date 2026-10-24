import { useState, useEffect, useCallback } from 'react'
import './App.css'

function App() {
  const [backendInfo, setBackendInfo] = useState(null)
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [folderPath, setFolderPath] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [analysisError, setAnalysisError] = useState(null)

  const [copyFeedback, setCopyFeedback] = useState({})

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  const copyToClipboard = useCallback(async (text, key) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopyFeedback(prev => ({ ...prev, [key]: { status: 'success', timestamp: Date.now() } }))
      setTimeout(() => {
        setCopyFeedback(prev => {
          const next = { ...prev }
          delete next[key]
          return next
        })
      }, 2000)
    } catch {
      setCopyFeedback(prev => ({ ...prev, [key]: { status: 'error', timestamp: Date.now() } }))
      setTimeout(() => {
        setCopyFeedback(prev => {
          const next = { ...prev }
          delete next[key]
          return next
        })
      }, 3000)
    }
  }, [])

  useEffect(() => {
    const fetchBackendInfo = async () => {
      try {
        const [infoRes, healthRes] = await Promise.all([
          fetch(`${API_URL}/`),
          fetch(`${API_URL}/health`)
        ])
        if (!infoRes.ok) throw new Error(`HTTP ${infoRes.status}: ${infoRes.statusText}`)
        if (!healthRes.ok) throw new Error(`HTTP ${healthRes.status}: ${healthRes.statusText}`)
        const info = await infoRes.json()
        const health = await healthRes.json()
        setBackendInfo(info)
        setHealth(health)
      } catch (err) {
        if (err instanceof TypeError && err.message === 'Failed to fetch') {
          setError('Network error: Cannot reach backend. Check if backend is running and CORS is configured.')
        } else {
          setError(err.message)
        }
      } finally {
        setLoading(false)
      }
    }

    fetchBackendInfo()
  }, [API_URL])

  const handleAnalyze = async (e) => {
    e.preventDefault()
    if (!folderPath.trim()) return

    setAnalyzing(true)
    setAnalysisError(null)
    setAnalysisResult(null)

    try {
      const res = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_path: folderPath.trim() })
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || `HTTP ${res.status}: ${res.statusText}`)
      }

      const data = await res.json()
      setAnalysisResult(data)
    } catch (err) {
      if (err instanceof TypeError && err.message === 'Failed to fetch') {
        setAnalysisError('Network error: Cannot reach backend. Check if backend is running.')
      } else {
        setAnalysisError(err.message)
      }
    } finally {
      setAnalyzing(false)
    }
  }

  const getStatusClass = (status) => {
    switch (status) {
      case 'success': return 'status-success'
      case 'error': return 'status-error'
      default: return 'status-skipped'
    }
  }

  const getStatusLabel = (status) => {
    const labels = {
      success: 'Processed',
      skipped_unsupported: 'Skipped (unsupported type)',
      skipped_empty: 'Skipped (empty)',
      skipped_unreadable: 'Skipped (unreadable)',
      skipped_encrypted: 'Skipped (encrypted)',
      skipped_oversized: 'Skipped (too large)',
      error: 'Error'
    }
    return labels[status] || status
  }

  return (
    <div className="app">
      <header>
        <h1>DustBunny</h1>
        <p className="subtitle">Privacy-first local AI file organizer</p>
      </header>

      <main>
        <section className="status-card">
          <h2>Backend Status</h2>
          {loading && <p className="loading">Connecting to backend...</p>}
          {error && <p className="error">Error: {error}</p>}
          {backendInfo && (
            <div className="info-grid">
              <div className="info-item">
                <span className="label">Name:</span>
                <span className="value">{backendInfo.name}</span>
              </div>
              <div className="info-item">
                <span className="label">Version:</span>
                <span className="value">{backendInfo.version}</span>
              </div>
              <div className="info-item">
                <span className="label">Description:</span>
                <span className="value">{backendInfo.description}</span>
              </div>
            </div>
          )}
          {health && (
            <div className={`health-status ${health.status === 'healthy' ? 'healthy' : 'unhealthy'}`}>
              Health: {health.status}
            </div>
          )}
        </section>

        <section className="analyze-card">
          <h2>Analyze Folder</h2>
          <p className="analyze-hint">
            Enter a folder path accessible to the backend running on your computer.
            The backend scans TXT, Markdown, and PDF files and returns AI-generated organization suggestions.
          </p>
          <form onSubmit={handleAnalyze} className="analyze-form">
            <div className="input-group">
              <label htmlFor="folder-path">Folder Path</label>
              <input
                id="folder-path"
                type="text"
                value={folderPath}
                onChange={(e) => setFolderPath(e.target.value)}
                placeholder="C:/Users/name/Documents or /home/user/documents"
                disabled={analyzing}
                required
              />
            </div>
            <button type="submit" disabled={analyzing || !folderPath.trim()} className="btn-primary">
              {analyzing ? 'Analyzing...' : 'Analyze'}
            </button>
          </form>
          {analysisError && <p className="error">{analysisError}</p>}
        </section>

        {analysisResult && (
          <section className="results-card">
            <h2>Analysis Results</h2>
            <div className="summary-grid">
              <div className="summary-item">
                <span className="summary-value">{analysisResult.total_files}</span>
                <span className="summary-label">Total Files</span>
              </div>
              <div className="summary-item success">
                <span className="summary-value">{analysisResult.processed_files}</span>
                <span className="summary-label">Processed</span>
              </div>
              <div className="summary-item skipped">
                <span className="summary-value">{analysisResult.skipped_files}</span>
                <span className="summary-label">Skipped</span>
              </div>
              <div className="summary-item error">
                <span className="summary-value">{analysisResult.error_files}</span>
                <span className="summary-label">Errors</span>
              </div>
            </div>

            <div className="results-list">
              {analysisResult.results.map((result, index) => (
                <article key={index} className={`result-card ${getStatusClass(result.status)}`}>
                  <header className="result-header">
                    <span className="result-filename">{result.filename}</span>
                    <span className={`result-status ${getStatusClass(result.status)}`}>
                      {getStatusLabel(result.status)}
                    </span>
                  </header>

                  {result.suggestion && (
                    <div className="suggestion">
                      <h4>AI Suggestion</h4>
                      <div className="suggestion-grid">
                        <div className="suggestion-field">
                          <span className="field-label">Category:</span>
                          <span className="field-value">{result.suggestion.category}</span>
                        </div>
                        <div className="suggestion-field">
                          <span className="field-label">Proposed Filename:</span>
                          <div className="field-value-with-copy">
                            <span className="field-value proposed-filename">{result.suggestion.suggested_filename}</span>
                            <button
                              type="button"
                              className="copy-btn"
                              onClick={() => copyToClipboard(result.suggestion.suggested_filename, `filename-${index}`)}
                              aria-label="Copy proposed filename"
                              title="Copy proposed filename"
                            >
                              {copyFeedback[`filename-${index}`]?.status === 'success' ? (
                                <span className="copy-icon success" aria-hidden="true">✓</span>
                              ) : copyFeedback[`filename-${index}`]?.status === 'error' ? (
                                <span className="copy-icon error" aria-hidden="true">✕</span>
                              ) : (
                                <span className="copy-icon" aria-hidden="true">⎘</span>
                              )}
                            </button>
                          </div>
                        </div>
                        <div className="suggestion-field">
                          <span className="field-label">Destination Folder:</span>
                          <div className="field-value-with-copy">
                            <span className="field-value proposed-folder">{result.suggestion.suggested_folder}</span>
                            <button
                              type="button"
                              className="copy-btn"
                              onClick={() => copyToClipboard(result.suggestion.suggested_folder, `folder-${index}`)}
                              aria-label="Copy destination folder"
                              title="Copy destination folder"
                            >
                              {copyFeedback[`folder-${index}`]?.status === 'success' ? (
                                <span className="copy-icon success" aria-hidden="true">✓</span>
                              ) : copyFeedback[`folder-${index}`]?.status === 'error' ? (
                                <span className="copy-icon error" aria-hidden="true">✕</span>
                              ) : (
                                <span className="copy-icon" aria-hidden="true">⎘</span>
                              )}
                            </button>
                          </div>
                        </div>
                        <div className="suggestion-field full-width">
                          <span className="field-label">Explanation:</span>
                          <span className="field-value">{result.suggestion.explanation}</span>
                        </div>
                        <div className="suggestion-field uncertainty-field">
                          <span className="field-label">Confidence:</span>
                          <div className="uncertainty-display">
                            <div className="uncertainty-bar" title="Approximate model self-assessment, not a calibrated probability">
                              <div
                                className="uncertainty-fill"
                                style={{
                                  width: `${(1 - result.suggestion.uncertainty) * 100}%`,
                                  backgroundColor: (1 - result.suggestion.uncertainty) * 100 >= 75 ? '#2e7d32' : (1 - result.suggestion.uncertainty) * 100 >= 50 ? '#f57c00' : '#c62828'
                                }}
                              ></div>
                            </div>
                            <span className="field-value uncertainty-label">
                              {((1 - result.suggestion.uncertainty) * 100 >= 75 ? 'High' : (1 - result.suggestion.uncertainty) * 100 >= 50 ? 'Medium' : 'Low')} confidence
                              {((1 - result.suggestion.uncertainty) * 100).toFixed(0)}%
                            </span>
                          </div>
                          <span className="uncertainty-note">(approximate model estimate)</span>
                        </div>
                      </div>
                      <p className="ai-disclaimer">All fields above are AI-generated suggestions. DustBunny never moves, renames, or deletes files.</p>
                    </div>
                  )}

                  {result.error_message && (
                    <div className="result-error">
                      <strong>Error:</strong> {result.error_message}
                    </div>
                  )}
                </article>
              ))}
            </div>
          </section>
        )}
      </main>

      <footer>
        <p>Hacktoberfest 2026 Week 3 Project</p>
      </footer>
    </div>
  )
}

export default App