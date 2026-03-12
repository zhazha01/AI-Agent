import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import logging

from app.config import settings
from app.models import DocumentChunk

logger = logging.getLogger(__name__)


class VectorStoreService:
    def __init__(self):
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.dimension = settings.EMBEDDING_DIMENSION
        
        self.client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT
        )
        
        self.collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info(f"Connected to ChromaDB: {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
        logger.info(f"Collection: {settings.CHROMA_COLLECTION}")

    def store_chunks(self, chunks: List[DocumentChunk]) -> int:
        if not chunks:
            return 0
        
        ids = [chunk.id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [self._chunk_to_metadata(chunk) for chunk in chunks]
        embeddings = self.embedding_model.encode(documents, show_progress_bar=False).tolist()
        
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )
        
        logger.info(f"Stored {len(chunks)} chunks to vector store")
        return len(chunks)

    def store_chunk(self, chunk: DocumentChunk) -> None:
        embedding = self.embedding_model.encode([chunk.content], show_progress_bar=False)[0].tolist()
        
        self.collection.add(
            ids=[chunk.id],
            documents=[chunk.content],
            metadatas=[self._chunk_to_metadata(chunk)],
            embeddings=[embedding]
        )

    def search(self, query: str, top_k: int = None, min_score: float = None) -> List[Dict[str, Any]]:
        top_k = top_k or settings.RETRIEVAL_TOP_K
        min_score = min_score or settings.RETRIEVAL_MIN_SCORE
        
        query_embedding = self.embedding_model.encode([query], show_progress_bar=False)[0].tolist()
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        search_results = []
        if results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                distance = results['distances'][0][i] if results['distances'] else 0
                score = 1 - distance
                
                if score >= min_score:
                    search_results.append({
                        'chunk_id': doc_id,
                        'content': results['documents'][0][i] if results['documents'] else '',
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'score': score
                    })
        
        logger.debug(f"Search returned {len(search_results)} results for query")
        return search_results

    def delete_collection(self) -> None:
        self.client.delete_collection(settings.CHROMA_COLLECTION)
        self.collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Deleted and recreated collection: {settings.CHROMA_COLLECTION}")

    def get_document_count(self) -> int:
        return self.collection.count()

    def _chunk_to_metadata(self, chunk: DocumentChunk) -> Dict[str, Any]:
        metadata = {
            'source_path': chunk.source_path,
            'relative_path': chunk.relative_path,
            'file_type': chunk.file_type.value,
            'chunk_index': chunk.chunk_index,
        }
        
        if chunk.package_name:
            metadata['package_name'] = chunk.package_name
        if chunk.class_name:
            metadata['class_name'] = chunk.class_name
        if chunk.method_name:
            metadata['method_name'] = chunk.method_name
        if chunk.annotation:
            metadata['annotation'] = chunk.annotation
        if chunk.start_line:
            metadata['start_line'] = chunk.start_line
        if chunk.end_line:
            metadata['end_line'] = chunk.end_line
        
        return metadata
