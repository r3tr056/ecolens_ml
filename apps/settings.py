import os
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Ecolens"
    DEBUG: bool = Field(default=False)
    API_V1_PREFIX: str = "/api/v1"
    
    # LLM Configuration
    LLAMA_MODEL_PATH: str = Field(..., env="LLAMA_MODEL_PATH")
    EMBEDDING_MODEL_PATH: str = Field(..., env="EMBEDDING_MODEL_PATH")
    
    # System Prompts
    SYSTEM_PROMPT: str = """You are EcoBuddy, an advanced AI search assistant. You provide comprehensive, factual 
                          information in response to user queries. When answering:
                          1. Cite your sources clearly
                          2. Acknowledge uncertainty when appropriate
                          3. Prioritize recent and authoritative information
                          4. Provide objective answers with relevant context
                          5. Format your responses to enhance readability with appropriate headings and bullet points
                          If you don't have sufficient information, say so instead of making up details."""
    
    # API Keys
    GOOGLE_SEARCH_API_KEY: Optional[str] = Field(default=None, env="GOOGLE_SEARCH_API_KEY")
    GOOGLE_CSE_ID: Optional[str] = Field(default=None, env="GOOGLE_CSE_ID")
    
    # Storage
    VECTOR_DB_PATH: str = Field(default="./.runtime/vectordb")
    EMBEDDING_CACHE_PATH: str = Field(default="./.runtime/embedding_cache")
    DOCUMENT_CACHE_PATH: str = Field(default="./.runtime/document_cache")

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds
    
    # Security
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    
    # Allowed CORS origins
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "https://yourdomain.com"]
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Redis for caching, rate limiting, and pub/sub
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()