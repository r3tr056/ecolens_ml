from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime

@dataclass
class SearchRequest:
    search_term: str
    image_url: Optional[str] = None
    stream: bool = False
    knowledge_sources: List[str] = field(default_factory=lambda: ['web'])
    filters: Dict[str, Any] = field(default_factory=dict)
    user_id: str = 'anonymous'

@dataclass
class ChatRequest:
    query: str
    result_id: str
    search_term: str
    stream: bool = False
    knowledge_sources: List[str] = field(default_factory=lambda: ['web'])
    user_id: str = 'anonymous'

@dataclass
class SearchResult:
    result_id: str
    title: str
    answer: str
    sources: List[Dict[str, str]]
    images: List[Dict[str, str]] = field(default_factory=list)
    related_queries: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'result_id': self.result_id,
            'title': self.title,
            'answer': self.answer,
            'sources': self.sources,
            'images': self.images,
            'related_queries': self.related_queries,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }

@dataclass
class ChatMessage:
    message_id: str
    result_id: str
    question: str
    answer: str
    sources: List[Dict[str, str]]
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'message_id': self.message_id,
            'result_id': self.result_id,
            'question': self.question,
            'answer': self.answer,
            'sources': self.sources,
            'created_at': self.created_at.isoformat()
        }

@dataclass
class KnowledgeSource:
    id: str
    name: str
    type: str  # 'web', 'database', 'file', 'api'
    config: Dict[str, Any]
    enabled: bool = True