import React, { useState, useRef, useEffect } from 'react'
import ResearchForm from './ResearchForm'
import ResearchResults from './ResearchResults'
import FileUpload from './FileUpload'
import './ResearchDashboard.css'

function ResearchDashboard({ agents, systemStatus }) {
  const [researchQuery, setResearchQuery] = useState('')
  const [results, setResults] = useState(null)
  const [isResearching, setIsResearching] = useState(false)
  const [agentUpdates, setAgentUpdates] = useState([])
  const wsRef = useRef(null)

  useEffect(() => {
    // Cleanup WebSocket on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const connectWebSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws`
    
    const ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      console.log('WebSocket connected')
    }
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      
      if (data.type === 'agent_update') {
        setAgentUpdates(prev => [...prev, data])
      } else if (data.type === 'research_complete') {
        setResults(data.result)
        setIsResearching(false)
        ws.close()
      } else if (data.type === 'status') {
        console.log('Status:', data.message)
      }
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      setIsResearching(false)
    }
    
    ws.onclose = () => {
      console.log('WebSocket disconnected')
    }
    
    wsRef.current = ws
    return ws
  }

  const handleResearch = async (query, options) => {
    setResearchQuery(query)
    setResults(null)
    setAgentUpdates([])
    setIsResearching(true)

    try {
      // Use WebSocket for real-time updates
      const ws = connectWebSocket()
      
      // Wait for connection
      await new Promise((resolve) => {
        if (ws.readyState === WebSocket.OPEN) {
          resolve()
        } else {
          ws.onopen = resolve
        }
      })

      // Send research request
      ws.send(JSON.stringify({
        type: 'research',
        query: query,
        context: {
          has_documents: options.useDocuments || false,
          use_web_search: options.useWebSearch !== false
        }
      }))
    } catch (error) {
      console.error('Research failed:', error)
      
      // Fallback to REST API
      try {
        const response = await fetch('/api/research', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query: query,
            use_documents: options.useDocuments || false,
            use_web_search: options.useWebSearch !== false
          })
        })
        
        const data = await response.json()
        setResults(data.result)
        setIsResearching(false)
      } catch (apiError) {
        console.error('API fallback failed:', apiError)
        setIsResearching(false)
      }
    }
  }

  const handleUploadSuccess = (result) => {
    console.log('File uploaded successfully:', result)
    // Optionally refresh document status or show notification
  }

  return (
    <div className="research-dashboard">
      <div className="card">
        <h2>Research Query</h2>
        <ResearchForm 
          onResearch={handleResearch}
          isResearching={isResearching}
          systemStatus={systemStatus}
        />
      </div>

      <div className="card">
        <FileUpload onUploadSuccess={handleUploadSuccess} />
      </div>

      {isResearching && (
        <div className="card">
          <h3>Research in Progress</h3>
          <div className="agent-updates">
            {agentUpdates.map((update, idx) => (
              <div key={idx} className="agent-update">
                <span className="agent-name">{update.agent}</span>
                <span className="agent-status">{update.status}</span>
              </div>
            ))}
            {agentUpdates.length === 0 && (
              <p className="loading">Initializing research agents...</p>
            )}
          </div>
        </div>
      )}

      {results && (
        <ResearchResults results={results} query={researchQuery} />
      )}
    </div>
  )
}

export default ResearchDashboard

