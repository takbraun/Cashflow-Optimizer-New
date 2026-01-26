"""
Configuration for the RAG system
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class RAGConfig:
    """Configuration class for RAG system"""

    # API Configuration
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

    # Model Configuration
    DEFAULT_MODEL = "claude-3-haiku-20240307"  # Cost-effective for frequent operations
    ANALYSIS_MODEL = "claude-sonnet-4-20250514"  # For deep analysis

    # ChromaDB Configuration
    BASE_DIR = Path(__file__).parent.parent
    CHROMA_PERSIST_DIR = str(BASE_DIR / "chroma_data")

    # Collection names
    EXPENSES_COLLECTION = "expenses"
    SUMMARIES_COLLECTION = "monthly_summaries"
    PATTERNS_COLLECTION = "patterns"

    # Retrieval Configuration
    DEFAULT_TOP_K = 10
    SIMILARITY_THRESHOLD = 0.7

    # Token limits
    MAX_CONTEXT_TOKENS = 4000
    MAX_OUTPUT_TOKENS = 1000

    # Caching
    CACHE_TTL_SECONDS = 3600  # 1 hour

    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present"""
        if not cls.ANTHROPIC_API_KEY:
            return False
        return True

    @classmethod
    def get_status(cls) -> dict:
        """Get configuration status"""
        return {
            'api_key_configured': bool(cls.ANTHROPIC_API_KEY),
            'chroma_dir': cls.CHROMA_PERSIST_DIR,
            'default_model': cls.DEFAULT_MODEL,
            'analysis_model': cls.ANALYSIS_MODEL
        }
