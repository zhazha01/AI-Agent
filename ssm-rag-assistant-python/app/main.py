import os
import tempfile
import logging
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import (
    RagResponse, IngestionResult, QueryRequest, IngestRequest,
    DocumentChunk
)
from app.ingestion import DocumentIngestionService
from app.vector_store import VectorStoreService
from app.rag_service import RagService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="RAG问答系统 - 基于LangChain的SSM项目智能助手"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

vector_store = None
rag_service = None
ingestion_service = None


@app.on_event("startup")
async def startup_event():
    global vector_store, rag_service, ingestion_service
    
    logger.info("Initializing SSM RAG Assistant...")
    
    vector_store = VectorStoreService()
    rag_service = RagService(vector_store)
    ingestion_service = DocumentIngestionService()
    
    project_path = Path(settings.PROJECT_PATH)
    if not project_path.exists():
        project_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created project directory: {project_path}")
    
    logger.info("SSM RAG Assistant initialized successfully")


@app.post("/v1/query", response_model=RagResponse)
async def query(request: QueryRequest):
    logger.info(f"Received query request: {request.question}")
    return rag_service.query(request.question)


@app.get("/v1/query", response_model=RagResponse)
async def query_get(question: str = Query(...)):
    logger.info(f"Received GET query request: {question}")
    return rag_service.query(question)


@app.post("/v1/ingest", response_model=IngestionResult)
async def ingest_project(request: IngestRequest):
    logger.info(f"Received ingest request for path: {request.project_path}")
    
    result = ingestion_service.ingest_project(request.project_path)
    
    if result.total_chunks > 0:
        all_chunks = []
        for summary in result.file_summaries:
            if summary.status == "SUCCESS":
                file_path = Path(request.project_path) / summary.path
                try:
                    chunks = ingestion_service.ingest_single_file(file_path, summary.path)
                    all_chunks.extend(chunks)
                except Exception as e:
                    logger.error(f"Error re-processing file {summary.path}: {e}")
        
        if all_chunks:
            vector_store.store_chunks(all_chunks)
    
    return result


@app.post("/v1/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    relative_path: str = None
):
    logger.info(f"Received file upload: {file.filename}")
    
    try:
        content = await file.read()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        
        rel_path = relative_path or file.filename
        chunks = ingestion_service.ingest_single_file(tmp_path, rel_path)
        
        vector_store.store_chunks(chunks)
        
        os.unlink(tmp_path)
        
        return {
            "fileName": file.filename,
            "chunkCount": len(chunks),
            "status": "SUCCESS"
        }
    except Exception as e:
        logger.error(f"Failed to process uploaded file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/search")
async def search(
    query: str = Query(...),
    top_k: int = Query(default=5)
):
    logger.info(f"Search request: {query} (topK={top_k})")
    results = vector_store.search(query, top_k=top_k)
    return results


@app.get("/v1/health")
async def health():
    return {
        "status": "UP",
        "timestamp": int(os.times().elapsed * 1000),
        "service": settings.APP_NAME,
        "documentCount": vector_store.get_document_count() if vector_store else 0
    }


@app.get("/v1/config")
async def get_config():
    return {
        "embeddingModel": settings.EMBEDDING_MODEL,
        "vectorStore": "ChromaDB",
        "llmProvider": "Ollama",
        "llmModel": settings.OLLAMA_MODEL,
        "projectPath": settings.PROJECT_PATH
    }


@app.get("/v1/stats")
async def get_stats():
    return {
        "documentCount": vector_store.get_document_count() if vector_store else 0,
        "collection": settings.CHROMA_COLLECTION
    }


static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/")
async def root():
    index_file = static_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "SSM RAG Assistant API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
