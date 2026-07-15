# Multi-Agent Research System

Multi-agent research and synthesis platform with a FastAPI backend, live WebSocket status updates, and a React monitoring UI.

Agents coordinate web research, document analysis, synthesis, and validation. Orchestration is a custom pipeline (LangGraph is a roadmap item, not required to run).

## Stack

- **Backend:** Python, FastAPI, WebSockets, OpenAI, Tavily
- **Frontend:** React (Vite)
- **Optional RAG:** Neo4j + Qdrant via Docker Compose

## Quick Start

```bash
git clone https://github.com/DevanshThakkar19/multi-agent-research-system.git
cd multi-agent-research-system
```

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY and TAVILY_API_KEY
python start_server.py
# or: uvicorn api.main:app --reload --port 8000
```

### Frontend (new terminal)

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL and use the management UI to start research runs.

### Optional document / RAG path

```bash
cd backend
docker compose up -d
pip install -r rag_requirements.txt
```

Ensure `NEO4J_PASSWORD` in `.env` matches `docker-compose.yml` (`multimodal_rag_2024`).

## Notes

- Core web-research path needs OpenAI + Tavily keys.
- Never commit `.env`.
- LangGraph is listed as future work in docs/roadmap — not a runtime dependency today.

## Author

**Devansh Thakkar** — MS Artificial Intelligence, Northeastern University  
[github.com/DevanshThakkar19](https://github.com/DevanshThakkar19)
