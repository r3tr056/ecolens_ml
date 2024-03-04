from langchain_community.graphs.graph_document import (
    Relationship as BaseRel,
)
from typing import Optional, List
from langchain_core.pydantic_v1 import BaseModel, Field

class Property(BaseModel):
    """ A single property consisting of key and value """
    key: str = Field(..., description="key")
    value: str = Field(..., description="value")

class Node(BaseModel):
    properties: Optional[List[Property]] = Field(None, description="List of node properties")

class Relationship(BaseRel):
    properties: Optional[List[Property]] = Field(None, description="List of relationship properties")

class KnowledgeGraph(BaseModel):
    """ Generate a knowledge graph with entities and relationships """
    nodes: List[Node] = Field(..., description="List of nodes in the knowledge graph")
    rels: List[Relationship] = Field(..., description="List of relationships in the knowledge graph")
