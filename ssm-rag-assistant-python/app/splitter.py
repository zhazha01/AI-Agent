import re
import uuid
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

from app.config import settings
from app.models import DocumentChunk, FileType


class JavaAwareSplitter:
    def __init__(self):
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
        self.min_chunk_size = settings.MIN_CHUNK_SIZE
        
        self.class_pattern = re.compile(
            r'(?:public|private|protected)?\s*(?:abstract\s+)?(?:class|interface|enum)\s+(\w+)',
            re.MULTILINE
        )
        self.method_pattern = re.compile(
            r'(?:public|private|protected)?\s*(?:static\s+)?(?:synchronized\s+)?'
            r'(?:final\s+)?(?:abstract\s+)?(?:native\s+)?'
            r'(?:<[^>]+>\s+)?(\w+(?:<[^>]+>)?)\s+(\w+)\s*\([^)]*\)',
            re.MULTILINE
        )
        self.package_pattern = re.compile(r'package\s+([\w.]+)\s*;')
        self.annotation_pattern = re.compile(r'@\w+(?:\([^)]*\))?')
        self.javadoc_pattern = re.compile(r'/\*\*[\s\S]*?\*/')
        self.import_pattern = re.compile(r'import\s+[\w.]+\s*;')

    def split_java_file(self, file_path: Path, relative_path: str, content: str) -> List[DocumentChunk]:
        chunks = []
        lines = content.split('\n')
        
        package_name = self._extract_package(content)
        classes = self._extract_classes(content)
        
        if not classes:
            return self._fallback_split(file_path, relative_path, content, FileType.JAVA)
        
        for class_info in classes:
            class_name = class_info['name']
            class_start = class_info['start_line']
            class_end = class_info['end_line']
            
            class_content = '\n'.join(lines[class_start:class_end])
            methods = self._extract_methods(class_content, class_start)
            
            if methods:
                for method in methods:
                    method_chunk = self._create_method_chunk(
                        file_path, relative_path, lines, package_name, 
                        class_name, method
                    )
                    if method_chunk:
                        chunks.append(method_chunk)
            else:
                class_chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    content=class_content,
                    source_path=str(file_path),
                    relative_path=relative_path,
                    file_type=FileType.JAVA,
                    package_name=package_name,
                    class_name=class_name,
                    start_line=class_start + 1,
                    end_line=class_end,
                    chunk_index=len(chunks),
                    total_chunks=1,
                    created_at=datetime.now()
                )
                chunks.append(class_chunk)
        
        return chunks if chunks else self._fallback_split(file_path, relative_path, content, FileType.JAVA)

    def _extract_package(self, content: str) -> Optional[str]:
        match = self.package_pattern.search(content)
        return match.group(1) if match else None

    def _extract_classes(self, content: str) -> List[dict]:
        classes = []
        lines = content.split('\n')
        
        for match in self.class_pattern.finditer(content):
            class_name = match.group(1)
            start_pos = match.start()
            start_line = content[:start_pos].count('\n')
            
            brace_count = 0
            end_line = start_line
            found_open = False
            
            for i in range(start_line, len(lines)):
                line = lines[i]
                brace_count += line.count('{') - line.count('}')
                if '{' in line:
                    found_open = True
                if found_open and brace_count == 0:
                    end_line = i + 1
                    break
            
            classes.append({
                'name': class_name,
                'start_line': start_line,
                'end_line': end_line
            })
        
        return classes

    def _extract_methods(self, class_content: str, offset: int) -> List[dict]:
        methods = []
        lines = class_content.split('\n')
        
        for match in self.method_pattern.finditer(class_content):
            return_type = match.group(1)
            method_name = match.group(2)
            
            if return_type in ['if', 'for', 'while', 'switch', 'catch', 'class', 'interface', 'new']:
                continue
            
            start_pos = match.start()
            start_line = class_content[:start_pos].count('\n')
            
            brace_count = 0
            end_line = start_line
            found_open = False
            
            for i in range(start_line, len(lines)):
                line = lines[i]
                brace_count += line.count('{') - line.count('}')
                if '{' in line:
                    found_open = True
                if found_open and brace_count == 0:
                    end_line = i + 1
                    break
            
            methods.append({
                'name': method_name,
                'return_type': return_type,
                'start_line': start_line + offset,
                'end_line': end_line + offset
            })
        
        return methods

    def _create_method_chunk(self, file_path: Path, relative_path: str, 
                             lines: List[str], package_name: Optional[str],
                             class_name: str, method: dict) -> Optional[DocumentChunk]:
        start_line = method['start_line']
        end_line = method['end_line']
        
        method_content = '\n'.join(lines[start_line:end_line])
        
        if len(method_content) < self.min_chunk_size:
            return None
        
        return DocumentChunk(
            id=str(uuid.uuid4()),
            content=method_content,
            source_path=str(file_path),
            relative_path=relative_path,
            file_type=FileType.JAVA,
            package_name=package_name,
            class_name=class_name,
            method_name=method['name'],
            start_line=start_line + 1,
            end_line=end_line,
            chunk_index=0,
            total_chunks=1,
            created_at=datetime.now()
        )

    def split_xml_file(self, file_path: Path, relative_path: str, content: str) -> List[DocumentChunk]:
        return self._split_by_lines(file_path, relative_path, content, FileType.XML)

    def split_sql_file(self, file_path: Path, relative_path: str, content: str) -> List[DocumentChunk]:
        chunks = []
        statements = re.split(r';\s*\n', content)
        
        line_number = 1
        for i, statement in enumerate(statements):
            statement = statement.strip()
            if not statement:
                continue
            
            statement_lines = statement.count('\n') + 1
            
            chunks.append(DocumentChunk(
                id=str(uuid.uuid4()),
                content=statement,
                source_path=str(file_path),
                relative_path=relative_path,
                file_type=FileType.SQL,
                start_line=line_number,
                end_line=line_number + statement_lines - 1,
                chunk_index=i,
                total_chunks=len(statements),
                created_at=datetime.now()
            ))
            
            line_number += statement_lines + 1
        
        return chunks

    def split_text_file(self, file_path: Path, relative_path: str, 
                        content: str, file_type: FileType) -> List[DocumentChunk]:
        return self._split_by_lines(file_path, relative_path, content, file_type)

    def _split_by_lines(self, file_path: Path, relative_path: str, 
                        content: str, file_type: FileType) -> List[DocumentChunk]:
        chunks = []
        lines = content.split('\n')
        
        current_chunk = []
        chunk_start_line = 1
        current_line = 1
        chunk_index = 0
        
        for line in lines:
            current_chunk.append(line)
            chunk_content = '\n'.join(current_chunk)
            
            if len(chunk_content) >= self.chunk_size:
                chunks.append(DocumentChunk(
                    id=str(uuid.uuid4()),
                    content=chunk_content,
                    source_path=str(file_path),
                    relative_path=relative_path,
                    file_type=file_type,
                    start_line=chunk_start_line,
                    end_line=current_line,
                    chunk_index=chunk_index,
                    total_chunks=1,
                    created_at=datetime.now()
                ))
                chunk_index += 1
                
                overlap_lines = current_chunk[-self.chunk_overlap:] if self.chunk_overlap > 0 else []
                chunk_start_line = max(1, current_line - len(overlap_lines) + 1)
                current_chunk = overlap_lines
            
            current_line += 1
        
        if current_chunk:
            chunks.append(DocumentChunk(
                id=str(uuid.uuid4()),
                content='\n'.join(current_chunk),
                source_path=str(file_path),
                relative_path=relative_path,
                file_type=file_type,
                start_line=chunk_start_line,
                end_line=current_line - 1,
                chunk_index=chunk_index,
                total_chunks=1,
                created_at=datetime.now()
            ))
        
        return chunks

    def _fallback_split(self, file_path: Path, relative_path: str, 
                        content: str, file_type: FileType) -> List[DocumentChunk]:
        return self._split_by_lines(file_path, relative_path, content, file_type)


def get_file_type(extension: str) -> FileType:
    ext_map = {
        '.java': FileType.JAVA,
        '.xml': FileType.XML,
        '.sql': FileType.SQL,
        '.properties': FileType.PROPERTIES,
        '.yml': FileType.YAML,
        '.yaml': FileType.YAML,
        '.md': FileType.MARKDOWN,
        '.txt': FileType.TEXT,
    }
    return ext_map.get(extension.lower(), FileType.UNKNOWN)
