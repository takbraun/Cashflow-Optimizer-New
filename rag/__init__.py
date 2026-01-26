"""
RAG (Retrieval-Augmented Generation) module for Cashflow-Optimizer
Provides intelligent financial insights and pattern analysis using Claude API
"""

from .insights_engine import InsightsEngine
from .vector_store import FinancialVectorStore
from .pattern_detector import PatternDetector
from .config import RAGConfig

__all__ = [
    'InsightsEngine',
    'FinancialVectorStore',
    'PatternDetector',
    'RAGConfig'
]
