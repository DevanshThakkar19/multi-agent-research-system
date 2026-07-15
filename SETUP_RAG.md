# 🔧 Setting Up RAG System for Document Analysis

## Quick Setup Steps

### 1. Start RAG Services (Docker)

```bash
cd backend
docker compose -f docker-compose.yml up -d
```

Wait 10-15 seconds for services to start.

### 2. Initialize Databases

```bash
cd backend
source venv/bin/activate
python rag_system/utils/setup_databases.py
```

### 3. Verify Services

- **Neo4j**: http://localhost:7474 (username: neo4j, password: from .env)
- **Qdrant**: http://localhost:6333

### 4. Re-upload Your Resume

After services are running:
1. Go to http://localhost:3000
2. Upload your resume again
3. Wait for "File processed successfully" message
4. Then query with "Use uploaded documents" checked

---

## Alternative: Use Original RAG UI

If Docker setup is complex, use the original RAG system:

```bash
cd /Users/devanshthakkar/multimodal-rag-system
source venv/bin/activate
streamlit run ui/app.py
```

Then upload files there - they'll be available to the multi-agent system!

---

## Current Status

✅ File upload working
✅ File saved to disk
❌ RAG indexing needs Neo4j + Qdrant running
❌ Document Analyzer needs RAG system initialized

Once RAG is set up, the Document Analyzer will extract information from your resume!






















