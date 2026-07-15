# Quick Start Guide

## Prerequisites Check

Before starting, ensure you have:
- ✅ Python 3.9+ installed
- ✅ Node.js 18+ installed
- ✅ Docker installed (for RAG system - optional)
- ✅ OpenAI API key
- ✅ Tavily API key (or alternative web search API)

## Step 1: Backend Setup (5 minutes)

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# If using document analysis, also install RAG dependencies
pip install -r rag_requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your API keys:
# - OPENAI_API_KEY
# - TAVILY_API_KEY (optional)
```

## Step 2: Start RAG Services (Optional - only if using document analysis)

```bash
# Start Docker services
docker compose -f docker-compose.yml up -d

# Wait 10-15 seconds, then initialize databases
python rag_system/utils/setup_databases.py
```

## Step 3: Start Backend Server

```bash
# Make sure you're in backend/ directory with venv activated
python -m api.main

# Or use uvicorn directly
uvicorn api.main:app --reload --port 8000
```

Backend should be running at `http://localhost:8000`

## Step 4: Frontend Setup (3 minutes)

```bash
# Open a new terminal
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend should be running at `http://localhost:3000`

## Step 5: Test the System

1. Open `http://localhost:3000` in your browser
2. Enter a research query, e.g.:
   - "What are the latest developments in transformer architectures?"
   - "Compare LangChain and LangGraph for agent orchestration"
3. Select options (use documents if you've uploaded any)
4. Click "Start Research"
5. Watch real-time agent updates
6. View comprehensive results

## Verify Installation

### Check Backend API

```bash
curl http://localhost:8000/api/status
```

Should return system status and agent information.

### Check Frontend

Open `http://localhost:3000` - you should see the research dashboard.

## Common Issues

### Backend won't start
- Check Python version: `python3 --version` (needs 3.9+)
- Verify virtual environment is activated
- Check all dependencies installed: `pip list`
- Verify `.env` file exists and has API keys

### Frontend won't connect
- Verify backend is running on port 8000
- Check browser console for errors
- Verify proxy settings in `vite.config.js`

### RAG system not working
- Ensure Docker services are running: `docker ps`
- Check Neo4j at `http://localhost:7474`
- Check Qdrant at `http://localhost:6333`
- Verify database credentials in `.env`

## Next Steps

1. **Upload Documents** (if using RAG):
   - Use the original RAG UI to upload documents
   - Or use the RAG API directly

2. **Customize Agents**:
   - Edit agent files in `backend/agents/`
   - Adjust search strategies, synthesis approaches

3. **Add Web Search APIs**:
   - Currently supports Tavily
   - Can add Serper or Perplexity in `web_researcher.py`

## API Examples

### REST API

```bash
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is agentic AI?",
    "use_documents": false,
    "use_web_search": true
  }'
```

### WebSocket (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'research',
    query: 'Your question here'
  }));
};
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

## Project Structure

```
multi-agent-research-system/
├── backend/
│   ├── agents/          # 5 specialized agents
│   ├── api/            # FastAPI backend
│   ├── core/           # Base classes & orchestrator
│   └── rag_system/     # Replicated RAG (original untouched)
├── frontend/           # React dashboard
└── README.md          # Full documentation
```

## Support

For detailed documentation, see `README.md`

For issues:
1. Check logs in terminal
2. Verify all services are running
3. Check API keys in `.env`
4. Review troubleshooting section in README.md






















