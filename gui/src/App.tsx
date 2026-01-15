import { useState, useCallback } from 'react'
import './App.css'
import { ThreadInput } from './components/ThreadInput'
import { AccountsInput } from './components/AccountsInput'
import { ProgressPanel } from './components/ProgressPanel'
import { ExportSection } from './components/ExportSection'
import { useExtraction, ExtractionStatus } from './hooks/useExtraction'

function App() {
  const [threadUrl, setThreadUrl] = useState('')
  const [accounts, setAccounts] = useState('')
  const [includeTimestamps, setIncludeTimestamps] = useState(false)
  const [includeCommentIds, setIncludeCommentIds] = useState(false)
  const [usePublicApi, setUsePublicApi] = useState(true)

  const {
    status,
    progress,
    result,
    error,
    startExtraction,
    reset
  } = useExtraction()

  const handleStart = useCallback(() => {
    const accountList = accounts
      .split(/[\n,]/)
      .map(a => a.trim())
      .filter(a => a.length > 0)

    startExtraction({
      threadUrl,
      accounts: accountList,
      includeTimestamps,
      includeCommentIds,
      usePublicApi
    })
  }, [threadUrl, accounts, includeTimestamps, includeCommentIds, usePublicApi, startExtraction])

  const isIdle = status === ExtractionStatus.IDLE
  const isRunning = status === ExtractionStatus.RUNNING
  const isComplete = status === ExtractionStatus.COMPLETE

  const canStart = isIdle && threadUrl.trim().length > 0 && accounts.trim().length > 0

  return (
    <div className="app">
      <header className="header">
        <h1>🗂️ Reddit Thread Archiver</h1>
        <p className="subtitle">Extract Q&A from Reddit AMAs and threads</p>
      </header>

      <main className="main">
        <section className="input-section">
          <ThreadInput
            value={threadUrl}
            onChange={setThreadUrl}
            disabled={isRunning}
          />

          <AccountsInput
            value={accounts}
            onChange={setAccounts}
            disabled={isRunning}
          />

          <div className="options-row">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={includeTimestamps}
                onChange={e => setIncludeTimestamps(e.target.checked)}
                disabled={isRunning}
              />
              Include timestamps
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={includeCommentIds}
                onChange={e => setIncludeCommentIds(e.target.checked)}
                disabled={isRunning}
              />
              Include comment IDs
            </label>
          </div>

          <div className="api-toggle">
            <span className={`toggle-label ${usePublicApi ? 'active' : ''}`}>Public API</span>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={!usePublicApi}
                onChange={e => setUsePublicApi(!e.target.checked)}
                disabled={isRunning}
              />
              <span className="toggle-slider"></span>
            </label>
            <span className={`toggle-label ${!usePublicApi ? 'active' : ''}`}>Authenticated</span>
          </div>
          {usePublicApi && (
            <p className="api-note">✓ No credentials required. Some deeply nested comments may be missed.</p>
          )}
          {!usePublicApi && (
            <p className="api-note">⚠ Requires Reddit API credentials in .env file.</p>
          )}

          <button
            className="start-button"
            onClick={handleStart}
            disabled={!canStart || isRunning}
          >
            {isRunning ? 'Extracting...' : 'Start Extraction'}
          </button>

          {isComplete && (
            <button className="reset-button" onClick={reset}>
              Start New Extraction
            </button>
          )}
        </section>

        <ProgressPanel
          status={status}
          progress={progress}
          error={error}
        />

        {isComplete && result && (
          <ExportSection
            result={result}
            includeTimestamps={includeTimestamps}
            includeCommentIds={includeCommentIds}
          />
        )}
      </main>

      <footer className="footer">
        <p>Respects Reddit API rate limits • Read-only • No data leaves your machine</p>
      </footer>
    </div>
  )
}

export default App
