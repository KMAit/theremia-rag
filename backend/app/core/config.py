from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Theremia RAG"
    DEBUG: bool = False

    # Proxy / networking
    TRUST_PROXY_HEADERS: bool = False

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./theremia.db"

    # Vector store
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # LLM / Embeddings
    OPENAI_API_KEY: str = ""
    DEFAULT_LLM_MODEL: str = "gpt-4o-mini"
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 50

    # RAG
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    RETRIEVAL_K: int = 5

    # JWT
    JWT_SECRET_KEY: str = "change_this_to_a_random_64_char_string_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
