import os
import json
import time
import uuid
import logging
import asyncio
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Generator, Union
from datetime import datetime, timedelta

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.faiss import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel

from apps.ecodome.generative_search.models import SearchRequest, ChatRequest, SearchResult, ChatMessage
from apps.ecodome.generative_search.knowledge_sources import KnowledgeSourceRegistry
from apps.ecodome.generative_search.prompts import (
    SYSTEM_PROMPT, 
    SEARCH_PROMPT, 
    QA_PROMPT, 
    RELATED_QUESTIONS_PROMPT
)
from apps.ecodome.generative_search.processors import DocumentProcessor, QueryProcessor
from apps.ecodome.generative_search.utils import create_or_load_vectorstore, get_cache_key

logger = logging.getLogger(__name__)

class GenSearchEngine:
    def __init__(self, llm, embedding_model, vector_store_path: Path, result_cache_path: Path, chunk_size: int = 1000, chunk_overlap: int = 200, max_sources: int = 10, cache_ttl: int = 3600):
        self.llm = llm
        self.embedding_model = embedding_model
        self.vector_store_path = vector_store_path
        self.result_cache_path = result_cache_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_sources = max_sources
        self.cache_ttl = cache_ttl

        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        self.result_cache_path.mkdir(parents=True, exist_ok=True)

        self.knowledge_registry = KnowledgeSourceRegistry()
        self.document_processor = DocumentProcessor(chunk_size, chunk_overlap)
        self.query_processor = QueryProcessor()

        self.active_searches = {}
        self.search_history = {}

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def search(self, request: SearchRequest) -> Dict[str, Any]:
        result_id = str(uuid.uuid4())
        start_time = time.time()

        cache_key = get_cache_key(request.search_term, request.image_url)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        try:
            processed_query = self.query_processor.process(request.search_term)
            
            knowledge_sources = []
            for source_name in request.knowledge_sources:
                source = self.knowledge_registry.get_source(source_name)
                if source:
                    knowledge_sources.append(source)

            if not knowledge_sources:
                knowledge_sources = [self.knowledge_registry.get_source("web")]

            all_documents = []
            sources_metadata = []

            for source in knowledge_sources:
                docs, meta = source.retrieve_knowledge(processed_query, request.image_url, request.filters)
                all_documents.extend(docs)
                sources_metadata.extend(meta)

            processed_docs = self.document_processor.process(all_documents)

            # create vector store
            vector_store_path = self.vector_store_path / result_id
            vector_store = create_or_load_vectorstore(docs=processed_docs, embedding_model=self.embedding_model, store_path=str(vector_store_path))

            retriever = vector_store.as_retriever(search_kwargs={"k": self.max_sources})

            # format system prompt
            system_prompt = SYSTEM_PROMPT.format(
                current_date=datetime.now().strftime("%Y-%m-%d"),
                search_term=request.search_term
            )

            # build RAG chain
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", SEARCH_PROMPT)
            ])

            def format_docs(docs):
                return "\n\n".join(doc.page_content for doc in docs)

            rag_chain = (
                RunnableParallel({
                    "context": retriever | format_docs,
                    "question": RunnablePassthrough(),
                })
                | prompt
                | self.llm
                | StrOutputParser()
            )

            # RAG chain for related questions
            related_prompt = ChatPromptTemplate.from_template(RELATED_QUESTIONS_PROMPT)
            related_chain = (
                related_prompt.format(search_term=request.search_term)
                | self.llm
                | StrOutputParser()
            )

            # execute chains
            answer = rag_chain.invoke(request.search_term)
            related_response = related_chain.invoke({})

            try:
                related_questions = [q.strip() for q in related_response.split('\n') if q.strip()][:5]
            except Exception as e:
                logger.warning(f"Failed to parse related questions: {e}")
                related_questions = []

            retreived_docs = retriever.invoke(request.search_term)
            sources = []
            for doc in retreived_docs[:self.max_sources]:
                if "source" in doc.metadata:
                    source_url = docs.metadata["source"]
                    source_title = doc.metadata.get("title", source_url)
                    sources.append({
                        "title": source_title,
                        "url": source_url,
                        "snippet": doc.page_content[:200] + "..." if len(docs.page_content) > 200 else doc.page_content
                    })

            search_result = SearchRequest(
                result_id=result_id,
                title=request.search_term,
                answer=answer,
                sources=sources,
                images=[],
                related_queries=related_questions,
                metadata={
                    "processing_time": time.time() - start_time,
                    "knowledge_sources": [ks.id for ks in knowledge_sources],
                    "query": request.search_term,
                    "timestamp": datetime.now().isoformat()
                }
            )

            self._cache_result(cache_key, search_result.to_dict())
            
            self.active_searches[result_id] = {
                "vector_store": vector_store,
                "query": request.search_term,
                "timestamp": datatime.now(),
                "user_id": request.user_id
            }

            if request.user_id not in self.search_history:
                self.search_history[request.user_id] = []

            self.search_history[request.user_id].append({
                "result_id": result_id,
                "query": request.search_term,
                "timestamp": datetime.now().isoformat(),
                "sources_count": len(sources)
            })

            if len(self.search_history[request.user_id]) > 100:
                self.search_history[request.user_id] = self.search_history[request.user_id][-100:]

            return search_result.to_dict()

        except Exception as e:
            logger.exception(f"Error during search: {str(e)}")
            return {
                "result_id": result_id,
                "error": str(e),
                "title": request.search_term,
                "answer": "I encountered an error while processing your search. Please try again later.",
                "sources": [],
                "images": [],
                "related_queries": [],
                "metadata": {
                    "error": str(e),
                    "processing_time": time.time() - start_time
                }
            }

    def chat(self, request: ChatRequest) -> Dict[str, Any]:
        """Process a follow-up chat message in the context of the previous search"""
        message_id = str(uuid.uuid4())

        try:
            search_context = self.active_searches.get(request.result_id)
            if not search_context:
                raise ValueError(f"No active search found with ID {request.result_id}")

            vector_store = search_context["vector_store"]
            previous_query = search_context["query"]

            retriever = vector_store.as_retriever(search_kwargs={"k": self.max_sources})

            system_prompt = SYSTEM_PROMPT.format(
                current_date=datetime.now().strftime("%Y-%m-%d"),
                search_term=previous_query
            )

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", QA_PROMPT)
            ])

            def format_docs(docs):
                return "\n\n".join(doc.page_content for doc in docs)

            rag_chain = (
                RunnableParallel({
                    "context": retriever | format_docs,
                    "question": RunnablePassthrough()
                })
                | prompt
                | self.llm
                | StrOutputParser()
            )

            # Execute chain
            answer = rag_chain.invoke(request.query)
            
            # Get sources
            retrieved_docs = retriever.invoke(request.query)
            sources = []
            for doc in retrieved_docs[:self.max_sources]:
                if "source" in doc.metadata:
                    source_url = doc.metadata["source"]
                    source_title = doc.metadata.get("title", source_url)
                    sources.append({
                        "title": source_title,
                        "url": source_url,
                        "snippet": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                    })
            
            # Create chat result
            chat_message = ChatMessage(
                message_id=message_id,
                result_id=request.result_id,
                question=request.query,
                answer=answer,
                sources=sources
            )

            if "messages" not in search_context:
                search_context["messages"] = []

            search_context["messages"].append(chat_message.to_dict())
            search_context["timestamp"] = datetime.now()

            return chat_message.to_dict()

        except Exception as e:
            logger.exception(f"Error during chat: {str(e)}")
            return {
                "message_id": message_id,
                "result_id": request.result_id,
                "question": request.query,
                "answer": "I encountered an error processing your question. Please try again.",
                "sources": [],
                "error": str(e)
            }

    def get_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        return self.search_history.get(user_id, [])

    def store_feedback(
        self,
        result_id: str,
        feedback_type: str,
        rating: int,
        comment: str = "",
        user_id: str = "anonymous"
    ) -> None:
        """Store user feedback for a search result"""
        pass

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a result from the cache if it exists and is not expired"""
        cache_file = self.result_cache_path / f"{cache_key}.json"
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r") as f:
                cached_data = json.load(f)

            created_at = datetime.fromisoformat(cached_data.get("metadata", {}).get("timestamp", ""))
            if datetime.now() - created_at > timedelta(seconds=self.cache_ttl):
                return None
                
            return cached_data
        except Exception as e:
            logger.warning(f"Error reading cache: {e}")
            return None 

    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Store a result in the cache"""
        cache_file = self.result_cache_path / f"{cache_key}.json"
        
        try:
            with open(cache_file, "w") as f:
                json.dump(result, f)
        except Exception as e:
            logger.warning(f"Error writing cache: {e}")
            
    def cleanup_old_searches(self, max_age_hours: int = 24) -> None:
        """Clean up search contexts that haven't been used for a while"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        to_remove = []
        for result_id, context in self.active_searches.items():
            if context["timestamp"] < cutoff_time:
                to_remove.append(result_id)
                
        for result_id in to_remove:
            del self.active_searches[result_id]
            
        logger.info(f"Cleaned up {len(to_remove)} old search contexts")