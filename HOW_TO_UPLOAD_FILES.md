# 📁 How to Upload Files for RAG System

## Option 1: Use RAG Streamlit UI (Recommended)

The RAG system has its own UI for uploading and processing files.

### Step 1: Start RAG Services (Docker)

```bash
cd /Users/devanshthakkar/multi-agent-research-system/backend
docker compose -f docker-compose.yml up -d
```

Wait 10-15 seconds for services to start.

### Step 2: Initialize Databases

```bash
cd backend
source venv/bin/activate
python rag_system/utils/setup_databases.py
```

### Step 3: Start RAG UI

```bash
cd backend
source venv/bin/activate
streamlit run rag_ui/app.py
```

This will open at **http://localhost:8501**

### Step 4: Upload Files

1. Open http://localhost:8501 in your browser
2. In the sidebar, click "Choose a file"
3. Select your file (PDF, TXT, DOCX, JPG, PNG, MP3, WAV, MP4, AVI)
4. Click "Process File"
5. Wait for processing to complete
6. File will be indexed in both vector DB and knowledge graph

### Step 5: Use in Multi-Agent System

Once files are uploaded and processed:
1. Go back to your Multi-Agent Research System (http://localhost:3000)
2. Check "Use uploaded documents (RAG system)"
3. Enter your query
4. The Document Analyzer Agent will query your uploaded documents!

---

## Option 2: Add Upload to Multi-Agent Frontend (Future Enhancement)

We can add file upload directly to the multi-agent frontend. This would require:
- Adding upload component to React frontend
- Creating upload endpoint in FastAPI backend
- Integrating with RAG pipeline

Would you like me to add this feature?

---

## Quick Test

After uploading files via RAG UI:

```bash
# Test if documents are available
curl http://localhost:8000/api/research \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What documents do I have?",
    "use_documents": true,
    "use_web_search": false
  }'
```

---

## Troubleshooting

**RAG UI won't start?**
- Check Docker services: `docker ps`
- Verify Neo4j: http://localhost:7474
- Verify Qdrant: http://localhost:6333

**Files not processing?**
- Check backend logs for errors
- Verify file format is supported
- Check database connections

**Documents not found in multi-agent system?**
- Make sure files were processed successfully in RAG UI
- Verify RAG system is initialized
- Check Document Analyzer Agent logs






















