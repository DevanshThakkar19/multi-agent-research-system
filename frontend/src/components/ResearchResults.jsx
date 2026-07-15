import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './ResearchResults.css'

function ResearchResults({ results, query }) {
  const [activeTab, setActiveTab] = useState('summary')

  if (!results) return null

  const synthesis = results.synthesis || {}
  const agentResults = results.agent_results || {}

  return (
    <div className="card research-results">
      <h2>Research Results</h2>
      <p className="query-display">Query: <strong>{query}</strong></p>

      <div className="tabs">
        <button
          className={activeTab === 'summary' ? 'active' : ''}
          onClick={() => setActiveTab('summary')}
        >
          Summary
        </button>
        <button
          className={activeTab === 'agents' ? 'active' : ''}
          onClick={() => setActiveTab('agents')}
        >
          Agent Results
        </button>
        <button
          className={activeTab === 'sources' ? 'active' : ''}
          onClick={() => setActiveTab('sources')}
        >
          Sources
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'summary' && (
          <div className="summary-content">
            <h3>Executive Summary</h3>
            <div className="report-section markdown-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {synthesis.report?.full_report || synthesis.report?.summary || synthesis.summary || 'No summary available'}
              </ReactMarkdown>
            </div>

            {synthesis.key_points && synthesis.key_points.length > 0 && (
              <div className="key-points">
                <h4>Key Points</h4>
                <ul>
                  {synthesis.key_points.map((point, idx) => (
                    <li key={idx}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {point}
                      </ReactMarkdown>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {synthesis.sources && synthesis.sources.length > 0 && (
              <div className="sources-preview">
                <h4>Sources ({synthesis.sources.length})</h4>
                <div className="sources-list">
                  {synthesis.sources.slice(0, 5).map((source, idx) => (
                    <div key={idx} className="source-item">
                      <a href={source.url} target="_blank" rel="noopener noreferrer">
                        {source.title || source.url}
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'agents' && (
          <div className="agent-results-content">
            {Object.entries(agentResults).map(([agentName, result]) => (
              <div key={agentName} className="agent-result-card">
                <h4>{agentName.replace('_', ' ').toUpperCase()}</h4>
                <div className={`status-badge ${result.success ? 'success' : 'error'}`}>
                  {result.success ? '✓ Success' : '✗ Failed'}
                </div>
                {result.success && result.data && (
                  <div className="agent-data">
                    {result.data.report ? (
                      <div className="markdown-content">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {result.data.report.full_report || result.data.report.summary || JSON.stringify(result.data, null, 2)}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <pre>{JSON.stringify(result.data, null, 2)}</pre>
                    )}
                  </div>
                )}
                {!result.success && result.error && (
                  <div className="error-message">{result.error}</div>
                )}
              </div>
            ))}
          </div>
        )}

        {activeTab === 'sources' && (
          <div className="sources-content">
            {synthesis.sources && synthesis.sources.length > 0 ? (
              <div className="sources-list-full">
                {synthesis.sources.map((source, idx) => (
                  <div key={idx} className="source-card">
                    <h4>{source.title || `Source ${idx + 1}`}</h4>
                    <a href={source.url} target="_blank" rel="noopener noreferrer">
                      {source.url}
                    </a>
                    {source.type && <span className="source-type">{source.type}</span>}
                  </div>
                ))}
              </div>
            ) : (
              <p>No sources available</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default ResearchResults

