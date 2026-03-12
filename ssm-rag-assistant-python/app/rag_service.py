import time
import logging
from typing import List, Optional

import httpx
from app.config import settings
from app.models import RagResponse, SourceReference
from app.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """你是一个专业的SSM项目开发助手，拥有丰富的Spring、SpringMVC、MyBatis开发经验。

你的职责是：
1. 基于提供的项目代码上下文，回答用户关于项目的问题
2. 像项目"老开发"一样，指出常见坑、推荐最佳实践
3. 在回答中引用具体的项目文件、类名、方法名
4. 提供可直接复制的代码示例

回答原则：
- 必须基于提供的上下文回答，不要编造不存在的内容
- 如果上下文中没有相关信息，明确告知用户
- 引用代码时，标注文件路径和行号
- 使用专业但易懂的语言，带"带新人"风格

回答格式：
1. 先给出直接答案
2. 再详细解释原理和背景
3. 最后给出代码示例（如有）
4. 附上引用的源文件位置"""


class RagService:
    def __init__(self, vector_store: VectorStoreService):
        self.vector_store = vector_store
        self.ollama_host = settings.OLLAMA_HOST
        self.model = settings.OLLAMA_MODEL

    def query(self, question: str) -> RagResponse:
        start_time = time.time()
        logger.info(f"Processing RAG query: {question}")

        search_results = self.vector_store.search(question)

        if not search_results:
            logger.warning(f"No relevant documents found for query: {question}")
            return RagResponse(
                question=question,
                answer="抱歉，在项目文档中没有找到与您问题相关的内容。请确保项目文件已正确导入，或尝试换一种方式提问。",
                sources=[],
                confidence=0.0,
                processing_time_ms=int((time.time() - start_time) * 1000),
                model=self.model
            )

        context = self._build_context(search_results)
        user_prompt = self._build_user_prompt(question, context)

        logger.debug(f"Context length: {len(context)} characters")

        answer = self._call_ollama(user_prompt)

        avg_score = sum(r['score'] for r in search_results) / len(search_results)

        sources = [self._convert_to_source_reference(r) for r in search_results]

        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(f"RAG query completed in {processing_time_ms}ms with confidence {avg_score:.2f}")

        return RagResponse(
            question=question,
            answer=answer,
            sources=sources,
            confidence=avg_score,
            processing_time_ms=processing_time_ms,
            model=self.model
        )

    def query_simple(self, question: str) -> str:
        search_results = self.vector_store.search(question)

        if not search_results:
            return "抱歉，没有找到相关信息。"

        context = self._build_context(search_results)
        user_prompt = self._build_user_prompt(question, context)

        return self._call_ollama(user_prompt)

    def _call_ollama(self, prompt: str) -> str:
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "system": SYSTEM_PROMPT,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "num_ctx": 4096
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return f"抱歉，调用 LLM 时发生错误: {str(e)}"

    def _build_context(self, results: List[dict]) -> str:
        context_parts = ["以下是项目中的相关代码片段：\n"]

        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            content = result.get('content', '')
            
            context_parts.append(f"【片段 {i}】")
            context_parts.append(f"文件: {metadata.get('relative_path', 'unknown')}")
            
            start_line = metadata.get('start_line')
            end_line = metadata.get('end_line')
            if start_line and end_line:
                context_parts.append(f" (行 {start_line}-{end_line})")
            context_parts.append("\n")
            
            class_name = metadata.get('class_name')
            method_name = metadata.get('method_name')
            if class_name:
                context_parts.append(f"类: {class_name}")
                if method_name:
                    context_parts.append(f" | 方法: {method_name}")
                context_parts.append("\n")
            
            file_type = metadata.get('file_type', '')
            lang_tag = self._get_language_tag(file_type)
            context_parts.append(f"```{lang_tag}\n")
            context_parts.append(content)
            context_parts.append("\n```\n\n")

        return "".join(context_parts)

    def _build_user_prompt(self, question: str, context: str) -> str:
        return f"""{context}

---

用户问题：{question}

请基于以上项目代码片段回答问题，并在回答中引用具体的文件路径和行号。"""

    def _convert_to_source_reference(self, result: dict) -> SourceReference:
        metadata = result.get('metadata', {})
        content = result.get('content', '')
        
        snippet = content[:200] + "..." if len(content) > 200 else content

        return SourceReference(
            chunk_id=result.get('chunk_id', ''),
            relative_path=metadata.get('relative_path', ''),
            class_name=metadata.get('class_name'),
            method_name=metadata.get('method_name'),
            start_line=metadata.get('start_line'),
            end_line=metadata.get('end_line'),
            snippet=snippet,
            score=result.get('score', 0.0),
            file_type=metadata.get('file_type', 'unknown')
        )

    def _get_language_tag(self, file_type: str) -> str:
        tags = {
            'java': 'java',
            'xml': 'xml',
            'sql': 'sql',
            'yaml': 'yaml',
            'properties': 'properties',
        }
        return tags.get(file_type.lower(), '')
