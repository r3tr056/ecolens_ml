import os
import logging
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union
from functools import lru_cache
from tqdm import tqdm

from langchain.prompts import ChatPromptTemplate
from langchain.document_loaders.directory import DirectoryLoader
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.chains import GraphCypherQAChain
from langchain.text_splitter import TokenTextSplitter
from langchain.vectorstores.faiss import FAISS
from langchain.schema import Document
from langchain_community.graphs.graph_document import (
    Node as BaseNode,
    Relationship as BaseRel,
    GraphDocument
)

from apps.ecodome.data_synthesis.knowledge.models import Relationship, Node, KnowledgeGraph
from apps.ecodome.data_synthesis.knowledge.cache import KnowledgeCacheManager

logger = logging.getLogger(__name__)

class KnowledgeBase:
    def __init__(self, n4j_graph, embedding_model, data_sources_path: str, cache_dir: Optional[str] = None, chunk_size: int = 1024, chunk_overlap: int = 100) -> None:
        self.n4j_graph = n4j_graph
        self.embedding_model = embedding_model
        self.data_sources_path = Path(data_sources_path)
        self.cache_dir = Path(cache_dir) if cache_dir else Path("./.runtime/kb_cache")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_manager = KnowledgeCacheManager(str(self.cache_dir))

        self.vector_stores = {}
        self._initialize_vector_stores()

        self.schema = self._get_schema()

    def _initialize_vector_stores(self):
        vector_store_path = self.cache_dir / "vector_stores"
        vector_store_path.mkdir(exist_ok=True)

        try:
            for store_dir in vector_store_path.iterdir():
                if store_dir.is_dir():
                    store_name = store_dir.name
                    try:
                        self.vector_stores[store_name] = FAISS.load_local(str(store_dir), self.embedding_model)
                        logger.info(f"Loaded vector store: {store_name}")
                    except Exception as e:
                        logger.warning(f"Could not load vector store {store_name}: {e}")
        except Exception as e:
            logger.warning(f"Error initializing vector stores: {e}")

    def _get_schema(self) -> Dict[str, Any]:
        """Get the schema information from Neo4j"""
        try:
            self.n4j_graph.refresh_schema()
            return self.n4j_graph.schema
        except Exception as e:
            logger.error(f"Failed to get schema: {e}")
            return {}

    def add_dict_to_graphdb(self, data):
        for node_label, properties in data.items():
            node = BaseNode(node_label, **properties)
            self.n4j_graph.create(node)

        for source_label, relationships in data.items():
            source_node = BaseNode(source_label)

            for relation_type, target_label in relationships.items():
                target_node = BaseNode(target_label)
                relation = BaseRel(source_node, relation_type, target_node)
                self.n4j_graph.create(relation)

    def format_property_key(self, s: str) -> str:
        """Format property keys in camelCase"""
        words = s.split()
        if not words:
            return s
        first_word = words[0].lower()
        capatalized_words = [word.capitalize() for word in words[1:]]
        return "".join([first_word] + capatalized_words)

    def props_to_dict(self, props) -> dict:
        """ Convert properties to a dictionary """
        properties = {}
        if not props:
            return properties
        for p in props:
            properties[self.format_property_key(p.key)] = p.value
        return properties

    def map_to_base_node(self, node: Node) -> BaseNode:
        properties = self.props_to_dict(node.properties) if node.properties else {}
        properties["name"] = node.id.title()
        return BaseNode(id=node.id.title(), type=node.type.capitalize(), properties=properties)

    def map_to_base_relationship(self, rel: Relationship) -> BaseRel:
        source = self.map_to_base_node(rel.source)
        target = self.map_to_base_node(rel.target)
        properties = self.props_to_dict(rel.properties) if rel.properties else {}
        return BaseRel(source=source, target=target, type=rel.type, properties=properties)

    def load_documents(self, refresh: bool = False) -> List[Document]:
        """Loads documents from data sources"""
        cache_key = f"loaded_docs_{self.data_sources_path}"

        if not refresh:
            cached_docs = self.cache_manager.get(cache_key)
            if cached_docs:
                logger.info(f"Loaded {len(cached_docs)} documents from cache")
                return cached_docs

        all_docs = []
        try:
            for file_path in self.data_sources_path.glob('**/*'):
                if file_path.is_file():
                    try:
                        if file_path.suffix.lower() == '.pdf':
                            loader = PyPDFLoader(str(file_path))
                            docs = loader.load()
                        elif file_path.suffix.lower() in ['.txt', '.md', '.json']:
                            loader = TextLoader(str(file_path))
                            docs = loader.load()
                        else:
                            # add more loaders here
                            continue

                        all_docs.extend(docs)
                    except Exception as e:
                        logger.warning(f"Failed to load {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error loading documents: {e}")

        if all_docs:
            self.cache_manager.set(cache_key, all_docs)
            logger.info(f"Loaded and cached {len(all_docs)} documents")
        return all_docs

    def split_docs(self, docs: List[Documents]) -> List[Document]:
        splitter = TokenTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        chunked_docs = splitter.split_documents(docs)
        return chunked_docs

    def build_knowledge_graph(self, llm, docs: Optional[List[Document]] = None, batch_size: int = 5) -> None:
        """Build knowledge graph from documents"""
        if docs is None:
            docs = self.load_documents()

        chunked_docs = self.split_docs(docs)
        total = len(chunked_docs)

        logger.info(f"Building knowledge graph from {total} document chunks")
        batches = [chunked_docs[i:i + batch_size] for i in range(0, len(chunked_docs), batch_size)]

        for i, batch in enumerate(batches):
            try:
                node_types = list(self.schema.get("node_props", {}).keys()) if self.schema else []
                rel_types = list(self.schema.get("rel_props", {}).keys()) if self.schema else []

                self._process_document_batch(llm, batch, node_types, rel_types)
            except Exception as e:
                logger.error(f"Error processing batch {i}: {e}")

        self._get_schema()
        logger.info("Knowledge graph build successfully")

    def _process_document_batch(self, llm, docs: List[Document], allowed_nodes: Optional[List[str]] = None, allowed_rels: Optional[List[str]] = None) -> None:
        """Process a batch of documents and add to the knowledge graph"""
        pass

    def extract_and_store_graph(self, llm, document, nodes, rels):
        extract_chain = self.get_knowledge_extraction_chain(llm, nodes, rels)
        data = extract_chain.run(document.page_content)
        graph_document = GraphDocument(
            nodes=[self.map_to_base_node(node) for node in data.nodes],
            relationships=[self.map_to_base_relationship(rel) for rel in data.rels],
            source=document
        )
        # store information into a graph
        self.n4j_graph.add_graph_documents([graph_document])

    
    def get_knowledge_extraction_chain(self, llm, allowed_nodes: Optional[List[str]] = None, allowed_rels: Optional[List[str]] = None):
        prompt = ChatPromptTemplate.from_messages(
            [(
                "system",
                f"""# Knowledge Graph Instructions for Gemini
    ## 1. Overview
    You are a top-tier algorithm designed for extracting information in structured formats to build a knowledge graph.
    - **Nodes** represent entities and concepts. They're akin to Wikipedia nodes.
    - The aim is to achieve simplicity and clarity in the knowledge graph, making it accessible for a vast audience.
    ## 2. Labeling Nodes
    - **Consistency**: Ensure you use basic or elementary types for node labels.
    - For example, when you identify an entity representing a person, always label it as **"person"**. Avoid using more specific terms like "mathematician" or "scientist".
    - **Node IDs**: Never utilize integers as node IDs. Node IDs should be names or human-readable identifiers found in the text.
    {'- **Allowed Node Labels:**' + ", ".join(allowed_nodes) if allowed_nodes else ""}
    {'- **Allowed Relationship Types**:' + ", ".join(allowed_rels) if allowed_rels else ""}
    ## 3. Handling Numerical Data and Dates
    - Numerical data, like age or other related information, should be incorporated as attributes or properties of the respective nodes.
    - **No Separate Nodes for Dates/Numbers**: Do not create separate nodes for dates or numerical values. Always attach them as attributes or properties of nodes.
    - **Property Format**: Properties must be in a key-value format.
    - **Quotation Marks**: Never use escaped single or double quotes within property values.
    - **Naming Convention**: Use camelCase for property keys, e.g., `birthDate`.
    ## 4. Coreference Resolution
    - **Maintain Entity Consistency**: When extracting entities, it's vital to ensure consistency.
    If an entity, such as "John Doe", is mentioned multiple times in the text but is referred to by different names or pronouns (e.g., "Joe", "he"),
    always use the most complete identifier for that entity throughout the knowledge graph. In this example, use "John Doe" as the entity ID.
    Remember, the knowledge graph should be coherent and easily understandable, so maintaining consistency in entity references is crucial.
    ## 5. Strict Compliance
    Adhere to the rules strictly. Non-compliance will result in termination."""
            ),
            ("human", "Use the given format to extract information from the following input: {input}"),
            ("human", "Tip: Make sure to answer in the correct format"),
        ])

        chain = prompt | llm | KnowledgeGraph
        return chain


    def get_conversation_chain(self, llm):
        self.n4j_graph.refresh_schema()
        cypher_chain = GraphCypherQAChain.from_llm(
            graph=self.n4j_graph,
            cypher_llm=llm,
            qa_llm=llm,
            validate_cypher=True,
            verbose=True
        )
        return cypher_chain