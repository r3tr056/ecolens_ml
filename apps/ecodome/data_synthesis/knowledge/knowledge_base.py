
from tqdm import tqdm
from typing import Optional, List

from langchain.prompts import ChatPromptTemplate
from langchain.document_loaders.directory import DirectoryLoader
from langchain.chains import GraphCypherQAChain
from langchain.text_splitter import TokenTextSplitter
from langchain_community.graphs.graph_document import (
    Node as BaseNode,
    Relationship as BaseRel,
    GraphDocument
)

from apps.ecodome.data_synthesis.knowledge.models import Relationship, Node, KnowledgeGraph

class KnowledgeBase:
    def __init__(self, n4j_graph, pdf_source_folder_path: str) -> None:
        """
        Load pdf and create a knowledge base using the Chroma vector DB
        """
        self.n4j_graph = n4j_graph
        self.pdf_source_folder_path = pdf_source_folder_path

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

    def load_pdfs(self):
        loader = DirectoryLoader(self.pdf_source_folder_path)
        loaded_pdfs = loader.load()
        return loaded_pdfs

    def split_docs(self, loaded_docs, chunk_size=2048, chunk_overlap=24):
        splitter = TokenTextSplitter(chunk_size, chunk_overlap)
        chunked_docs = splitter.split_documents(loaded_docs)
        return chunked_docs

    def add_docs_to_graph(self, chunked_docs, llm):
        for i, d in tqdm(enumerate(chunked_docs), total=len(chunked_docs)):
            self.extract_and_storage_graph(llm=llm, document=d)

    def add_text_to_graph(self, text, llm):
        extract_chain = self.get_knowledge_extraction_chain(llm=llm)
        data = extract_chain.run(text)
        graph_document = GraphDocument(
            nodes=[self.map_to_base_node(node) for node in data.nodes],
            relationships=[self.map_to_base_relationship(rel) for rel in data.rels],
        )
        self.n4j_graph.add_graph_documents([graph_document])

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
                f"""# Knowledge Graph Instructions for GPT-4
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