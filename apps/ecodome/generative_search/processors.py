import re
import logging
import unicodedata
from typing import List
from bs4 import BeautifulSoup
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Process and prepare documents for use in the search engine"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
    def process(self, documents: List[Document]) -> List[Document]:
        """Process a list of documents"""
        if not documents:
            return []
        
        processed_docs = self.text_splitter.split_documents(documents)
        for doc in processed_docs:
            doc.page_content = self._clean_text(doc.page_content)
            
        return processed_docs
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Normalize Unicode to canonical form (e.g., convert full-width to half-width characters)
        text = unicodedata.normalize('NFKC', text)
        # Remove HTML tags (useful for webpages)
        text = self._strip_html(text)
        # Remove URLs from the text
        text = re.sub(r'http[s]?://\S+', '', text)
        # Remove standalone page numbers or digits often found in PDFs
        text = re.sub(r'(?m)^\s*\d+\s*$', '', text)
        # Normalize quotes and dashes
        text = text.replace("“", '"').replace("”", '"')
        text = text.replace("‘", "'").replace("’", "'")
        text = text.replace("–", "-").replace("—", "-")
        # Remove boilerplate such as page footers (example pattern: "Page X of Y")
        text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
         # Replace multiple newlines with a single newline
        text = re.sub(r'\n+', '\n', text)
        # Replace multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text)
        # Final trim of leading/trailing whitespace
        text = text.strip()
        return text

    def _strip_html(self, text: str) -> str:
        if '<' in text and '>' in text:
            soup = BeautifulSoup(text, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        return text

class QueryProcessor:
    """Process and enhance search queries"""
    
    def process(self, query: str) -> str:
        """Process a search query"""
        query = query.strip()
        query = re.sub(r'[?!.]+(?=[?!.])', '', query)
        
        # Ensure the query ends with a question mark if it's a question
        if (query.lower().startswith('what') or 
            query.lower().startswith('how') or 
            query.lower().startswith('why') or 
            query.lower().startswith('when') or 
            query.lower().startswith('where') or 
            query.lower().startswith('which') or 
            query.lower().startswith('who') or 
            query.lower().startswith('is') or 
            query.lower().startswith('are') or 
            query.lower().startswith('can') or 
            query.lower().startswith('do') or 
            query.lower().startswith('does')):
            if not query.endswith('?'):
                query += '?'
                
        return query