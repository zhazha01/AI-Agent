from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class FileType(str, Enum):
    JAVA = "java"
    XML = "xml"
    SQL = "sql"
    PROPERTIES = "properties"
    YAML = "yaml"
    MARKDOWN = "md"
    TEXT = "txt"
    UNKNOWN = "unknown"


class DocumentChunk(BaseModel):
    id: str
    content: str
    source_path: str
    relative_path: str
    file_type: FileType
    package_name: Optional[str] = None
    class_name: Optional[str] = None
    method_name: Optional[str] = None
    annotation: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    chunk_index: int = 0
    total_chunks: int = 1
    created_at: datetime = datetime.now()
    metadata: Dict[str, Any] = {}

    def get_display_name(self) -> str:
        if self.class_name and self.method_name:
            return f"{self.class_name}.{self.method_name}()"
        elif self.class_name:
            return self.class_name
        elif self.relative_path:
            return self.relative_path
        return "Unknown"

    def get_location_info(self) -> str:
        info = self.relative_path or "unknown"
        if self.start_line and self.end_line:
            info += f":L{self.start_line}-L{self.end_line}"
        return info


class SourceReference(BaseModel):
    chunk_id: str
    relative_path: str
    class_name: Optional[str] = None
    method_name: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    snippet: str
    score: float
    file_type: str


class RagResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourceReference]
    confidence: float
    processing_time_ms: int
    model: str


class FileSummary(BaseModel):
    path: str
    file_type: FileType
    chunk_count: int
    status: str
    error_message: Optional[str] = None


class IngestionResult(BaseModel):
    project_path: str
    total_files: int
    processed_files: int
    skipped_files: int
    total_chunks: int
    processing_time_ms: int
    errors: List[str]
    file_summaries: List[FileSummary]


class QueryRequest(BaseModel):
    question: str


class IngestRequest(BaseModel):
    project_path: str
