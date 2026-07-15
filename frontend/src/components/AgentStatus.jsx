import React, { useState, useEffect } from 'react'
import './AgentStatus.css'

function AgentStatus({ agents }) {
  const [status, setStatus] = useState(null)

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch('/api/status')
        const data = await response.json()
        setStatus(data)
      } catch (error) {
        console.error('Failed to fetch status:', error)
      }
    }

    fetchStatus()
    const interval = setInterval(fetchStatus, 30000) // Update every 30 seconds

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="agent-status">
      <div className="card">
        <h2>System Status</h2>
        {status && (
          <div className="status-info">
            <div className="status-badge operational">
              {status.status === 'operational' ? '✓ Operational' : '⚠ Issues'}
            </div>
          </div>
        )}

        <h3>Available Agents</h3>
        <div className="agents-list">
          {agents.map((agent, idx) => (
            <div key={idx} className="agent-card">
              <div className="agent-header">
                <h4>{agent.name.replace('_', ' ').toUpperCase()}</h4>
                <span className="agent-status-badge">Ready</span>
              </div>
              <p className="agent-description">{agent.description}</p>
              {agent.capabilities && agent.capabilities.tools && (
                <div className="agent-tools">
                  <strong>Tools:</strong> {agent.capabilities.tools.join(', ')}
                </div>
              )}
            </div>
          ))}
        </div>

        {status && status.execution_history && (
          <div className="execution-history">
            <h3>Recent Activity</h3>
            <p className="history-count">
              Total Executions: {status.execution_history.total_executions || 0}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default AgentStatus






















