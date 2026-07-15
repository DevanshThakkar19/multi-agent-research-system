# 🚀 How to Start the Server

## Step 1: Set up your API keys

```bash
cd /Users/devanshthakkar/multi-agent-research-system/backend

# The .env file has been created for you
# Now edit it and add your OpenAI API key:
nano .env
# OR
open -e .env
```

**Minimum required**: Add your `OPENAI_API_KEY`:
```env
OPENAI_API_KEY=sk-your-actual-key-here
```

## Step 2: Start the Backend Server

```bash
# Make sure you're in the backend directory
cd /Users/devanshthakkar/multi-agent-research-system/backend

# Activate virtual environment
source venv/bin/activate

# Start the server
python start_server.py
```

You should see:
```
🚀 Starting Multi-Agent Research System Backend...
📡 API will be available at http://localhost:8000
📚 API docs at http://localhost:8000/docs
```

## Step 3: Start the Frontend (in a NEW terminal)

```bash
cd /Users/devanshthakkar/multi-agent-research-system/frontend
npm install  # If you haven't already
npm run dev
```

## Step 4: Open in Browser

- **Frontend**: http://localhost:3000
- **Backend API Docs**: http://localhost:8000/docs
- **Backend Status**: http://localhost:8000/api/status

## Quick Test

Once both are running, test the backend:
```bash
curl http://localhost:8000/api/status
```

## Troubleshooting

**Server won't start?**
- ✅ Check `.env` file exists: `ls -la backend/.env`
- ✅ Verify API key is set: `grep OPENAI_API_KEY backend/.env`
- ✅ Make sure venv is activated: `which python` should show `venv/bin/python`

**Port already in use?**
- Kill existing process: `lsof -ti:8000 | xargs kill`
- Or change port in `start_server.py`






















