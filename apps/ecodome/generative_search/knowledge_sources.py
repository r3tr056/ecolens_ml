import os
import logging
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional

from langchain_community.document_loaders import WebBaseLoader
from langchain.schema import Document
from apps.tasks.google_search import async_google_image_search, async_product_google_search
from apps.ecodome.data_synthesis.knowledge.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

class KnowledgeSource(ABC):
    """Abstract base class for knowledge sources"""
    
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name
    
    @abstractmethod
    def retrieve_knowledge(
        self, 
        query: str, 
        image_url: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Document], List[Dict[str, Any]]]:
        """
        Retrieve knowledge from the source
        
        Returns:
            Tuple containing:
                - List of Documents
                - List of metadata about the sources
        """
        pass

class WebKnowledgeSource(KnowledgeSource):
    """Knowledge source that retrieves information from the web"""
    
    def __init__(self):
        super().__init__(id="web", name="Web Search")
    
    def retrieve_knowledge(
        self, 
        query: str, 
        image_url: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Document], List[Dict[str, Any]]]:
        documents = []
        metadata = []
        
        try:
            if image_url:
                # Use image search
                subject, webpage_url, image_results = async_google_image_search(image_url=image_url)
                
                if webpage_url:
                    loader = WebBaseLoader(webpage_url)
                    webpage_docs = loader.load()
                    documents.extend(webpage_docs)
                    
                    metadata.append({
                        "source_type": "image_search",
                        "url": webpage_url,
                        "title": subject or "Image Search Result",
                        "images": image_results or []
                    })
            else:
                search_results = async_product_google_search(query)
                
                if isinstance(search_results, list):
                    for result in search_results:
                        if isinstance(result, dict) and "url" in result:
                            try:
                                loader = WebBaseLoader(result["url"])
                                page_docs = loader.load()
                                documents.extend(page_docs)
                                
                                metadata.append({
                                    "source_type": "web_search",
                                    "url": result["url"],
                                    "title": result.get("title", result["url"]),
                                    "snippet": result.get("snippet", "")
                                })
                            except Exception as e:
                                logger.warning(f"Failed to load {result['url']}: {str(e)}")
                elif isinstance(search_results, str):
                    documents.append(Document(page_content=search_results, metadata={"source": "web_search"}))
                    
                    metadata.append({
                        "source_type": "web_search",
                        "title": f"Search results for: {query}",
                        "content": search_results[:200] + "..." if len(search_results) > 200 else search_results
                    })
        
        except Exception as e:
            logger.exception(f"Error retrieving web knowledge: {str(e)}")
            documents.append(Document(
                page_content=f"Error retrieving information for query: {query}",
                metadata={"source": "error", "error": str(e)}
            ))
            metadata.append({
                "source_type": "error",
                "error": str(e)
            })
        
        return documents, metadata

class KnowledgeBaseSource(KnowledgeSource):
    """Knowledge source that retrieves information from internal knowledge base"""
    
    def __init__(self, knowledge_base: KnowledgeBase):
        super().__init__(id="knowledge_base", name="Internal Knowledge Base")
        self.knowledge_base = knowledge_base
    
    def retrieve_knowledge(
        self, 
        query: str, 
        image_url: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Document], List[Dict[str, Any]]]:
        documents = []
        metadata = []
        
        try:
            # Query the knowledge base
            kb_results = self.knowledge_base.query(query, filters=filters or {})
            
            for result in kb_results:
                documents.append(Document(
                    page_content=result.get("content", ""),
                    metadata={
                        "source": "knowledge_base",
                        "id": result.get("id", ""),
                        "title": result.get("title", ""),
                        "category": result.get("category", "")
                    }
                ))
                
                metadata.append({
                    "source_type": "knowledge_base",
                    "id": result.get("id", ""),
                    "title": result.get("title", ""),
                    "category": result.get("category", "")
                })
                
        except Exception as e:
            logger.exception(f"Error retrieving knowledge base data: {str(e)}")
            # Return an empty result set with error info
            documents.append(Document(
                page_content=f"Error retrieving information from knowledge base for query: {query}",
                metadata={"source": "error", "error": str(e)}
            ))
            metadata.append({
                "source_type": "error",
                "error": str(e)
            })
        
        return documents, metadata

class KnowledgeSourceRegistry:
    """Registry of available knowledge sources"""
    
    def __init__(self):
        self.sources = {}
        self._initialize_default_sources()
    
    def _initialize_default_sources(self):
        """Initialize default knowledge sources"""
        # Always add web search
        self.register(WebKnowledgeSource())
        
        # Try to add knowledge base if available
        try:
            from apps.ecodome.data_synthesis.knowledge.knowledge_base import get_knowledge_base_instance
            kb = get_knowledge_base_instance()
            self.register(KnowledgeBaseSource(kb))
        except ImportError:
            logger.warning("Knowledge base not available")
        except Exception as e:
            logger.exception(f"Failed to initialize knowledge base: {str(e)}")
    
    def register(self, source: KnowledgeSource):
        """Register a knowledge source"""
        self.sources[source.id] = source
        logger.info(f"Registered knowledge source: {source.id} ({source.name})")
    
    def get_source(self, source_id: str) -> Optional[KnowledgeSource]:
        """Get a knowledge source by ID"""
        return self.sources.get(source_id)
    
    def get_all_sources(self) -> List[KnowledgeSource]:
        """Get all registered knowledge sources"""
        return list(self.sources.values())