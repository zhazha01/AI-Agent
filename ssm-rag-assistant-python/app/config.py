from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "SSM RAG Assistant"
    APP_VERSION: str = "1.0.0"
    
    PROJECT_PATH: str = "./project-files"
    EXCLUDE_DIRS: List[str] = ["target", ".git", ".idea", "node_modules", "build", "dist", ".mvn", "__pycache__"]
    INCLUDE_EXTENSIONS: List[str] = [".java", ".xml", ".sql", ".properties", ".yml", ".yaml", ".md", ".txt"]
    
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    MIN_CHUNK_SIZE: int = 100
    
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION: str = "ssm_project_knowledge"
    
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:7b"
    
    RETRIEVAL_TOP_K: int = 5
    RETRIEVAL_MIN_SCORE: float = 0.3
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
