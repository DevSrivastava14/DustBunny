import { useState, useEffect, useCallback } from 'react'
import './App.css'

function App() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [folderPath, setFolderPath] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [analysisError, setAnalysisError] = useState(null)

  const [copyFeedback, setCopyFeedback] = useState({})
  const [pickerSupported] = useState(() => 'showDirectoryPicker' in window)
  const [pickedFolderName, setPickedFolderName] = useState(null)

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
    const checkBackend = async () => {
      try {
        const res = await fetch(`${API_URL}/`)
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      } catch (err) {
        if (err instanceof TypeError && err.message === 'Failed to fetch') {
          setError('Cannot reach backend. Is it running on port 8000?')
        } else {
          setError(err.message)
        }
      } finally {
        setLoading(false)
      }
    }

    checkBackend()
  }, [API_URL])

  const readFileAsText = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => resolve(e.target.result)
      reader.onerror = () => reject(new Error('Failed to read file'))
      reader.readAsText(file)
    })
  }

  const readFileAsBase64 = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => {
        const result = e.target.result
        const base64 = result.split(',')[1] || result
        resolve(base64)
      }
      reader.onerror = () => reject(new Error('Failed to read file as base64'))
      reader.readAsDataURL(file)
    })
  }

  const processDirectory = async (dirHandle, files = [], pathPrefix = '') => {
    for await (const [name, handle] of dirHandle.entries()) {
      const fullPath = pathPrefix ? `${pathPrefix}/${name}` : name
      if (handle.kind === 'file') {
        const lowerName = name.toLowerCase()
        if (lowerName.endsWith('.txt') || lowerName.endsWith('.md')) {
          try {
            const file = await handle.getFile()
            const content = await readFileAsText(file)
            files.push({ filename: fullPath, content })
          } catch {
            files.push({ filename: fullPath, content: '', error: 'Failed to read file' })
          }
        } else if (lowerName.endsWith('.pdf')) {
          try {
            const file = await handle.getFile()
            if (file.size > 10 * 1024 * 1024) {
              files.push({
                filename: fullPath,
                content: '',
                content_base64: '',
                error: `File exceeds 10MB limit`
              })
            } else {
              const content_base64 = await readFileAsBase64(file)
              files.push({ filename: fullPath, content: '', content_base64 })
            }
          } catch {
            files.push({ filename: fullPath, content: '', content_base64: '', error: 'Failed to read file' })
          }
        }
      } else if (handle.kind === 'directory') {
        await processDirectory(handle, files, fullPath)
      }
    }
    return files
  }

  const handleBrowseFolder = async () => {
    if (!pickerSupported) return

    try {
      const dirHandle = await window.showDirectoryPicker({ mode: 'read' })
      setPickedFolderName(dirHandle.name)
      setAnalyzing(true)
      setAnalysisError(null)
      setAnalysisResult(null)

      const files = await processDirectory(dirHandle)

      if (files.length === 0) {
        setAnalysisError('No supported files (.txt, .md, .pdf) found in the selected folder.')
        setAnalyzing(false)
        return
      }

      const res = await fetch(`${API_URL}/analyze-contents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files })
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
      } else if (err.name === 'AbortError') {
      } else {
        setAnalysisError(err.message)
      }
    } finally {
      setAnalyzing(false)
    }
  }

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
      case 'success': return 'success'
      case 'error': return 'error'
      default: return 'skipped'
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

  const getConfidenceClass = (uncertainty) => {
    const confidence = (1 - uncertainty) * 100
    if (confidence >= 75) return 'high'
    if (confidence >= 50) return 'medium'
    return 'low'
  }

  return (
    <div className="app">
      <header>
        <h1>DustBunny</h1>
        <p className="subtitle">Privacy-first local AI file organizer</p>
      </header>

      <main>
        {loading && (
          <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
            <div className="loading-spinner" style={{ margin: '0 auto 1rem' }}></div>
            <p className="hint">Connecting to backend...</p>
          </div>
        )}

        {error && !loading && (
          <div className="card error" style={{ textAlign: 'center' }}>
            <strong>Backend Unavailable</strong>
            <p style={{ margin: '0.5rem 0 0', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
              {error}
            </p>
            <p style={{ margin: '1rem 0 0', fontSize: '0.8rem', color: 'var(--text-subtle)' }}>
              Start the backend with <code>uvicorn app.main:app --port 8000</code> from the <code>backend/</code> directory.
            </p>
          </div>
        )}

        {!loading && !error && (
          <>
            <section className="card analyze-card">
              <h2>Analyze Folder</h2>
              <p className="hint">
                Enter a folder path accessible to the backend, or use the Browse button to pick a folder
                (supports .txt, .md, and .pdf files).
              </p>
              <form onSubmit={handleAnalyze} className="form">
                <div className="input-group">
                  <label htmlFor="folder-path">Folder Path</label>
                  <div className="input-wrapper">
                    <input
                      id="folder-path"
                      type="text"
                      value={folderPath}
                      onChange={(e) => { setFolderPath(e.target.value); setPickedFolderName(null); }}
                      placeholder="C:/Users/name/Documents or /home/user/documents"
                      disabled={analyzing}
                      required
                    />
                    {pickerSupported && (
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={handleBrowseFolder}
                        disabled={analyzing}
                        aria-label="Browse for folder"
                        title="Pick a folder using the browser's native directory picker"
                      >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{flexShrink: 0}}>
                          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                        </svg>
                        Browse…
                      </button>
                    )}
                  </div>
                </div>
                {pickedFolderName && (
                  <p className="folder-hint">Selected: {pickedFolderName} (browser picker — .txt, .md, .pdf)</p>
                )}
                <button type="submit" disabled={analyzing || !folderPath.trim()} className="btn btn-primary">
                  {analyzing ? (
                    <>
                      <svg className="loading-spinner" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{marginRight: '0.5rem'}}>
                        <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
                        <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
                      </svg>
                      Analyzing…
                    </>
                  ) : 'Analyze'}
                </button>
              </form>
              {analysisError && <div className="error">{analysisError}</div>}
            </section>

            {analysisResult && (
              <section className="card results-card">
                <h2>Analysis Results</h2>
                <div className="summary-grid">
                  <div className="summary-item total">
                    <span className="summary-value">{analysisResult.total_files}</span>
                    <span className="summary-label">Total</span>
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
                              <span className="field-label">Category</span>
                              <span className="field-value">{result.suggestion.category}</span>
                            </div>
                            <div className="suggestion-field">
                              <span className="field-label">Proposed Filename</span>
                              <div className="field-value-with-copy">
                                <span className="proposed-value proposed-filename">{result.suggestion.suggested_filename}</span>
                                <button
                                  type="button"
                                  className="copy-btn"
                                  onClick={() => copyToClipboard(result.suggestion.suggested_filename, `filename-${index}`)}
                                  aria-label="Copy proposed filename"
                                  title="Copy proposed filename"
                                >
                                  {copyFeedback[`filename-${index}`]?.status === 'success' ? (
                                    <span className="copy-icon success">✓</span>
                                  ) : copyFeedback[`filename-${index}`]?.status === 'error' ? (
                                    <span className="copy-icon error">✕</span>
                                  ) : (
                                    <svg className="copy-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                                    </svg>
                                  )}
                                </button>
                              </div>
                            </div>
                            <div className="suggestion-field">
                              <span className="field-label">Destination Folder</span>
                              <div className="field-value-with-copy">
                                <span className="proposed-value proposed-folder">{result.suggestion.suggested_folder}</span>
                                <button
                                  type="button"
                                  className="copy-btn"
                                  onClick={() => copyToClipboard(result.suggestion.suggested_folder, `folder-${index}`)}
                                  aria-label="Copy destination folder"
                                  title="Copy destination folder"
                                >
                                  {copyFeedback[`folder-${index}`]?.status === 'success' ? (
                                    <span className="copy-icon success">✓</span>
                                  ) : copyFeedback[`folder-${index}`]?.status === 'error' ? (
                                    <span className="copy-icon error">✕</span>
                                  ) : (
                                    <svg className="copy-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                                    </svg>
                                  )}
                                </button>
                              </div>
                            </div>
                            <div className="suggestion-field full-width">
                              <span className="field-label">Explanation</span>
                              <span className="field-value">{result.suggestion.explanation}</span>
                            </div>
                            <div className="suggestion-field uncertainty-field">
                              <span className="field-label">Confidence</span>
                              <div className="uncertainty-display">
                                <div className="uncertainty-bar" title="Approximate model self-assessment, not a calibrated probability">
                                  <div
                                    className="uncertainty-fill"
                                    style={{
                                      width: `${(1 - result.suggestion.uncertainty) * 100}%`,
                                      backgroundColor: (1 - result.suggestion.uncertainty) * 100 >= 75 ? 'var(--success)' : (1 - result.suggestion.uncertainty) * 100 >= 50 ? 'var(--warning)' : 'var(--error)'
                                    }}
                                  ></div>
                                </div>
                                <span className={`uncertainty-label ${getConfidenceClass(result.suggestion.uncertainty)}`}>
                                  {((1 - result.suggestion.uncertainty) * 100 >= 75 ? 'High' : (1 - result.suggestion.uncertainty) * 100 >= 50 ? 'Medium' : 'Low')} confidence
                                  {((1 - result.suggestion.uncertainty) * 100).toFixed(0)}%
                                </span>
                              </div>
                              <span className="uncertainty-note">(approximate model estimate)</span>
                            </div>
                          </div>
                          <p className="disclaimer">All fields above are AI-generated suggestions. DustBunny never moves, renames, or deletes files.</p>
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
          </>
        )}
      </main>

      <footer>
        <p>Hacktoberfest 2026 • <a href="https://github.com" target="_blank" rel="noopener noreferrer">Open Source</a> • Built with React, FastAPI, and Ollama</p>
      </footer>
    </div>
  )
}

export default App