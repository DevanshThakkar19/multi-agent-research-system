"""
FastAPI Backend for Multi-Agent Research System
Provides REST API and WebSocket support for real-time agent updates.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

import sys
import os
# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from core.orchestrator import MultiAgentOrchestrator
from agents import (
    ResearchCoordinatorAgent,
    WebResearcherAgent,
    DocumentAnalyzerAgent,
    SynthesisAgent,
    ValidatorAgent
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Multi-Agent Research System API",
    description="API for autonomous multi-agent research and knowledge synthesis",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents
agents = {
    "research_coordinator": ResearchCoordinatorAgent(),
    "web_researcher": WebResearcherAgent(),
    "document_analyzer": DocumentAnalyzerAgent(),
    "synthesis_agent": SynthesisAgent(),
    "validator_agent": ValidatorAgent()
}

# Initialize orchestrator
orchestrator = MultiAgentOrchestrator(agents)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        await websocket.send_json(message)
    
    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")

manager = ConnectionManager()


# Request/Response Models
class ResearchRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None
    use_documents: bool = True
    use_web_search: bool = True


class ResearchResponse(BaseModel):
    success: bool
    query: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str


# API Routes
@app.get("/")
async def root():
    return {
        "message": "Multi-Agent Research System API",
        "version": "1.0.0",
        "endpoints": {
            "research": "/api/research",
            "websocket": "/ws",
            "status": "/api/status",
            "agents": "/api/agents"
        }
    }


@app.get("/api/status")
async def get_status():
    """Get system status and agent information"""
    return {
        "status": "operational",
        "agents": {name: agent.get_capabilities() for name, agent in agents.items()},
        "execution_history": orchestrator.get_execution_status()
    }


@app.get("/api/agents")
async def get_agents():
    """Get information about all available agents"""
    return {
        "agents": {
            name: {
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.get_capabilities()
            }
            for name, agent in agents.items()
        }
    }


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file for processing by the RAG system
    
    Supports: PDF, TXT, DOCX, JPG, PNG, MP3, WAV, MP4, AVI
    """
    try:
        # Create upload directory
        upload_dir = Path("data/raw")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = upload_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Process file with RAG system if available
        processing_result = {
            "filename": file.filename,
            "size": len(content),
            "saved_path": str(file_path),
            "status": "saved"
        }
        
        # Try to process with RAG pipeline
        try:
            import sys
            rag_path = Path(__file__).parent.parent / "rag_system"
            if rag_path.exists():
                sys.path.insert(0, str(rag_path))
                from pipeline import RAGPipeline
                
                pipeline = RAGPipeline()
                result = pipeline.ingest_and_index(str(file_path))
                processing_result["status"] = "processed"
                processing_result["rag_result"] = result
        except Exception as e:
            logger.warning(f"RAG processing failed: {e}")
            processing_result["rag_error"] = str(e)
        
        return {
            "success": True,
            "message": f"File {file.filename} uploaded successfully",
            "result": processing_result
        }
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/research", response_model=ResearchResponse)
async def conduct_research(request: ResearchRequest):
    """
    Conduct research using the multi-agent system
    
    Args:
        request: Research query and options
        
    Returns:
        Research results from all agents
    """
    try:
        context = request.context or {}
        context["has_documents"] = request.use_documents
        context["use_web_search"] = request.use_web_search
        context["query"] = request.query
        
        # Coordinate research
        result = await orchestrator.coordinate_research(
            query=request.query,
            context=context
        )
        
        return ResearchResponse(
            success=True,
            query=request.query,
            result=result,
            timestamp=result.get("timestamp", "")
        )
    except Exception as e:
        logger.error(f"Research failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time research updates
    
    Clients can send research queries and receive real-time updates
    as agents complete their tasks.
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data.get("type") == "research":
                query = data.get("query", "")
                context = data.get("context", {})
                
                # Send initial acknowledgment
                await manager.send_personal_message({
                    "type": "status",
                    "message": "Research started",
                    "query": query
                }, websocket)
                
                # Helper to convert AgentResult to dict
                def convert_to_dict(obj):
                    """Convert AgentResult to dict"""
                    if hasattr(obj, 'success'):
                        return {
                            "success": obj.success,
                            "data": obj.data,
                            "metadata": obj.metadata,
                            "error": obj.error,
                            "timestamp": obj.timestamp
                        }
                    return obj
                
                # Conduct research with real-time updates
                async def progress_callback(agent_name: str, status: str, data: Any):
                    # Convert data if it's an AgentResult
                    serializable_data = convert_to_dict(data) if hasattr(data, 'success') else data
                    await manager.send_personal_message({
                        "type": "agent_update",
                        "agent": agent_name,
                        "status": status,
                        "data": serializable_data
                    }, websocket)
                
                # Execute research
                result = await orchestrator.coordinate_research(query, context)
                
                # Convert AgentResult objects to dicts for JSON serialization
                def convert_agent_results(obj):
                    """Recursively convert AgentResult objects to dicts"""
                    if isinstance(obj, dict):
                        return {k: convert_agent_results(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_agent_results(item) for item in obj]
                    elif hasattr(obj, '__dict__'):
                        # Handle AgentResult and other objects
                        if hasattr(obj, 'success'):
                            # It's an AgentResult
                            return {
                                "success": obj.success,
                                "data": convert_agent_results(obj.data),
                                "metadata": convert_agent_results(obj.metadata),
                                "error": obj.error,
                                "timestamp": obj.timestamp
                            }
                        return convert_agent_results(obj.__dict__)
                    return obj
                
                # Convert result for JSON serialization
                serializable_result = convert_agent_results(result)
                
                # Send final result
                await manager.send_personal_message({
                    "type": "research_complete",
                    "result": serializable_result
                }, websocket)
            
            elif data.get("type") == "ping":
                await manager.send_personal_message({
                    "type": "pong"
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

