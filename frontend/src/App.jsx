import React, { useState, useEffect } from 'react'
import ResearchDashboard from './components/ResearchDashboard'
import AgentStatus from './components/AgentStatus'
import './App.css'

function App() {
  const [agents, setAgents] = useState([])
  const [systemStatus, setSystemStatus] = useState('loading')

  useEffect(() => {
    // Fetch agent information
    fetch('/api/agents')
      .then(res => res.json())
      .then(data => {
        setAgents(Object.values(data.agents || {}))
        setSystemStatus('ready')
      })
      .catch(err => {
        console.error('Failed to fetch agents:', err)
        setSystemStatus('error')
      })
  }, [])

  return (
    <div className="App">
      <header className="App-header">
        <h1>Multi-Agent Research System</h1>
        <p className="subtitle">Autonomous Research & Knowledge Synthesis</p>
      </header>
      
      <main className="App-main">
        <div className="dashboard-container">
          <ResearchDashboard agents={agents} systemStatus={systemStatus} />
          <AgentStatus agents={agents} />
        </div>
      </main>
    </div>
  )
}

export default App






















