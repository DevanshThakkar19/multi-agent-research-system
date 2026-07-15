# 🚀 Quick Start - Multi-Agent Research System

## ✅ Dependencies Installed!

Great! You've successfully installed all dependencies. Now let's start the system.

## Step 1: Configure Environment Variables

```bash
cd backend
cp .env.example .env
# Edit .env and add your API keys:
# - OPENAI_API_KEY=your_key_here
# - TAVILY_API_KEY=your_key_here (optional, for web search)
```

## Step 2: Start Backend Server

```bash
# Make sure you're in backend/ directory with venv activated
source venv/bin/activate

# Option 1: Use the startup script (recommended)
python start_server.py

# Option 2: Use uvicorn directly
uvicorn api.main:app --reload --port 8000
```

The backend will start at **http://localhost:8000**

## Step 3: Start Frontend (in a new terminal)

```bash
cd frontend
npm install  # If you haven't already
npm run dev
```

The frontend will start at **http://localhost:3000**

## Step 4: Test the System

1. Open **http://localhost:3000** in your browser
2. Enter a research query, e.g.:
   - "What are the latest developments in transformer architectures?"
   - "Compare LangChain and LangGraph for agent orchestration"
3. Click "Start Research"
4. Watch real-time agent updates!

## API Endpoints

Once backend is running:
- **API Docs**: http://localhost:8000/docs
- **Status**: http://localhost:8000/api/status
- **Agents Info**: http://localhost:8000/api/agents

## Troubleshooting

### Backend won't start
- ✅ Check `.env` file exists and has `OPENAI_API_KEY`
- ✅ Verify virtual environment is activated: `source venv/bin/activate`
- ✅ Check Python version: `python --version` (needs 3.9+)

### Frontend won't connect
- ✅ Verify backend is running on port 8000
- ✅ Check browser console for errors
- ✅ Verify proxy settings in `frontend/vite.config.js`

### Import Errors
- ✅ All import issues have been fixed!
- ✅ Make sure you're running from the `backend/` directory
- ✅ Use `python start_server.py` for easiest startup

## Next Steps

1. **Set up API keys** in `.env` file
2. **Start backend**: `python start_server.py`
3. **Start frontend**: `npm run dev` (in frontend/)
4. **Test**: Open http://localhost:3000

## Need Help?

- Check `README.md` for full documentation
- Check `QUICK_START.md` for detailed setup guide
- Check `PROJECT_SUMMARY.md` for architecture overview






















