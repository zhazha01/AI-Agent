import os
import time
from pathlib import Path
from typing import List

from app.config import settings
from app.models import DocumentChunk, FileType, IngestionResult, FileSummary
from app.splitter import JavaAwareSplitter, get_file_type


class DocumentIngestionService:
    def __init__(self):
        self.splitter = JavaAwareSplitter()
        self.exclude_dirs = set(settings.EXCLUDE_DIRS)
        self.include_extensions = set(settings.INCLUDE_EXTENSIONS)

    def ingest_project(self, project_path: str) -> IngestionResult:
        start_time = time.time()
        root_path = Path(project_path)
        
        if not root_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        errors = []
        file_summaries = []
        total_files = 0
        processed_files = 0
        skipped_files = 0
        total_chunks = 0

        for file_path in self._walk_directory(root_path):
            total_files += 1
            relative_path = str(file_path.relative_to(root_path))
            extension = file_path.suffix
            
            if not self._should_process(extension):
                skipped_files += 1
                continue

            try:
                content = file_path.read_text(encoding='utf-8')
                chunks = self._process_file(file_path, relative_path, content, extension)
                
                file_summaries.append(FileSummary(
                    path=relative_path,
                    file_type=get_file_type(extension),
                    chunk_count=len(chunks),
                    status="SUCCESS"
                ))
                
                processed_files += 1
                total_chunks += len(chunks)
                
            except Exception as e:
                error_msg = f"Failed to process {file_path}: {str(e)}"
                errors.append(error_msg)
                file_summaries.append(FileSummary(
                    path=relative_path,
                    file_type=get_file_type(extension),
                    chunk_count=0,
                    status="FAILED",
                    error_message=str(e)
                ))

        processing_time_ms = int((time.time() - start_time) * 1000)

        return IngestionResult(
            project_path=project_path,
            total_files=total_files,
            processed_files=processed_files,
            skipped_files=skipped_files,
            total_chunks=total_chunks,
            processing_time_ms=processing_time_ms,
            errors=errors,
            file_summaries=file_summaries
        )

    def ingest_single_file(self, file_path: Path, relative_path: str) -> List[DocumentChunk]:
        content = file_path.read_text(encoding='utf-8')
        extension = file_path.suffix
        return self._process_file(file_path, relative_path, content, extension)

    def _walk_directory(self, root_path: Path):
        for item in root_path.rglob('*'):
            if item.is_file():
                if not any(excluded in item.parts for excluded in self.exclude_dirs):
                    yield item

    def _should_process(self, extension: str) -> bool:
        if not extension:
            return False
        return extension.lower() in self.include_extensions

    def _process_file(self, file_path: Path, relative_path: str, 
                      content: str, extension: str) -> List[DocumentChunk]:
        file_type = get_file_type(extension)
        
        if file_type == FileType.JAVA:
            return self.splitter.split_java_file(file_path, relative_path, content)
        elif file_type == FileType.XML:
            return self.splitter.split_xml_file(file_path, relative_path, content)
        elif file_type == FileType.SQL:
            return self.splitter.split_sql_file(file_path, relative_path, content)
        else:
            return self.splitter.split_text_file(file_path, relative_path, content, file_type)
