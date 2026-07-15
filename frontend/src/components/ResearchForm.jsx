import React, { useState } from 'react'
import './ResearchForm.css'

function ResearchForm({ onResearch, isResearching, systemStatus }) {
  const [query, setQuery] = useState('')
  const [useDocuments, setUseDocuments] = useState(true)
  const [useWebSearch, setUseWebSearch] = useState(true)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim() && !isResearching && systemStatus === 'ready') {
      onResearch(query, {
        useDocuments,
        useWebSearch
      })
    }
  }

  return (
    <form onSubmit={handleSubmit} className="research-form">
      <div className="form-group">
        <label htmlFor="query">Research Query</label>
        <textarea
          id="query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter your research question... (e.g., 'Research the latest developments in transformer architectures')"
          rows={4}
          disabled={isResearching || systemStatus !== 'ready'}
          required
        />
      </div>

      <div className="form-options">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={useDocuments}
            onChange={(e) => setUseDocuments(e.target.checked)}
            disabled={isResearching || systemStatus !== 'ready'}
          />
          <span>Use uploaded documents (RAG system)</span>
        </label>

        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={useWebSearch}
            onChange={(e) => setUseWebSearch(e.target.checked)}
            disabled={isResearching || systemStatus !== 'ready'}
          />
          <span>Search the web</span>
        </label>
      </div>

      <button
        type="submit"
        className="research-button"
        disabled={!query.trim() || isResearching || systemStatus !== 'ready'}
      >
        {isResearching ? 'Researching...' : 'Start Research'}
      </button>

      {systemStatus === 'loading' && (
        <p className="status-message">Loading system...</p>
      )}
      {systemStatus === 'error' && (
        <p className="status-message error">Failed to connect to backend</p>
      )}
    </form>
  )
}

export default ResearchForm






















