"""
Financial Retriever - Retrieves relevant context from vector store
"""

from typing import List, Dict, Optional, Any
from .vector_store import FinancialVectorStore
from .config import RAGConfig


class FinancialRetriever:
    """Retrieves relevant financial context for RAG queries"""

    def __init__(self, vector_store: FinancialVectorStore):
        """
        Initialize retriever with vector store

        Args:
            vector_store: FinancialVectorStore instance
        """
        self.vector_store = vector_store

    def get_relevant_context(
        self,
        query: str,
        collections: List[str] = None,
        top_k: int = None,
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Get relevant documents from specified collections

        Args:
            query: Search query
            collections: List of collection names to search ('expenses', 'summaries', 'patterns')
            top_k: Number of results per collection
            filters: Optional metadata filters

        Returns:
            List of relevant documents with metadata
        """
        if collections is None:
            collections = ['expenses', 'summaries', 'patterns']

        if top_k is None:
            top_k = RAGConfig.DEFAULT_TOP_K

        results = []

        for collection in collections:
            if collection == 'expenses':
                query_result = self.vector_store.query_expenses(
                    query=query,
                    n_results=top_k,
                    where=filters
                )
            elif collection == 'summaries':
                query_result = self.vector_store.query_summaries(
                    query=query,
                    n_results=top_k,
                    where=filters
                )
            elif collection == 'patterns':
                query_result = self.vector_store.query_patterns(
                    query=query,
                    n_results=top_k,
                    where=filters
                )
            else:
                continue

            # Process results
            if query_result and query_result.get('documents'):
                for i, doc in enumerate(query_result['documents'][0]):
                    results.append({
                        'collection': collection,
                        'document': doc,
                        'metadata': query_result['metadatas'][0][i] if query_result.get('metadatas') else {},
                        'id': query_result['ids'][0][i] if query_result.get('ids') else None,
                        'distance': query_result['distances'][0][i] if query_result.get('distances') else None
                    })

        # Sort by relevance (lower distance = more relevant)
        results.sort(key=lambda x: x.get('distance', float('inf')))

        return results

    def get_expense_history(
        self,
        category: Optional[str] = None,
        month: Optional[str] = None,
        top_k: int = 20
    ) -> List[Dict]:
        """
        Get expense history with optional filters

        Args:
            category: Filter by category
            month: Filter by month (YYYY-MM format)
            top_k: Number of results

        Returns:
            List of expense documents
        """
        filters = {}
        if category:
            filters['category'] = category
        if month:
            filters['month'] = month

        query = "gastos "
        if category:
            query += f"en {category} "
        if month:
            query += f"del mes {month}"

        result = self.vector_store.query_expenses(
            query=query.strip(),
            n_results=top_k,
            where=filters if filters else None
        )

        expenses = []
        if result and result.get('documents'):
            for i, doc in enumerate(result['documents'][0]):
                expenses.append({
                    'document': doc,
                    'metadata': result['metadatas'][0][i] if result.get('metadatas') else {},
                    'id': result['ids'][0][i] if result.get('ids') else None
                })

        return expenses

    def get_category_context(
        self,
        categories: List[str],
        months: int = 3
    ) -> str:
        """
        Get context for specific categories

        Args:
            categories: List of category names
            months: Number of months to look back

        Returns:
            Formatted context string
        """
        context_parts = []

        for category in categories:
            # Query for this category
            result = self.vector_store.query_expenses(
                query=f"gastos en categoría {category}",
                n_results=15,
                where={'category': category}
            )

            if result and result.get('documents') and result['documents'][0]:
                total = sum(
                    meta.get('amount', 0)
                    for meta in result.get('metadatas', [[]])[0]
                )
                count = len(result['documents'][0])
                context_parts.append(
                    f"Categoría {category}: {count} transacciones, total ${total:.2f}"
                )

        return "\n".join(context_parts) if context_parts else "Sin datos de categorías"

    def get_monthly_summaries(
        self,
        months: int = 3
    ) -> List[Dict]:
        """
        Get recent monthly summaries

        Args:
            months: Number of months to retrieve

        Returns:
            List of summary documents
        """
        result = self.vector_store.query_summaries(
            query="resumen financiero mensual",
            n_results=months
        )

        summaries = []
        if result and result.get('documents'):
            for i, doc in enumerate(result['documents'][0]):
                summaries.append({
                    'document': doc,
                    'metadata': result['metadatas'][0][i] if result.get('metadatas') else {},
                    'month': result['metadatas'][0][i].get('month') if result.get('metadatas') else None
                })

        return summaries

    def get_patterns_for_category(
        self,
        category: str
    ) -> List[Dict]:
        """
        Get detected patterns for a specific category

        Args:
            category: Category name

        Returns:
            List of pattern documents
        """
        result = self.vector_store.query_patterns(
            query=f"patrones de gasto en {category}",
            n_results=5,
            where={'category': category}
        )

        patterns = []
        if result and result.get('documents'):
            for i, doc in enumerate(result['documents'][0]):
                patterns.append({
                    'document': doc,
                    'metadata': result['metadatas'][0][i] if result.get('metadatas') else {}
                })

        return patterns

    def format_context_for_llm(
        self,
        documents: List[Dict],
        max_tokens: int = None
    ) -> str:
        """
        Format retrieved documents into a context string for LLM

        Args:
            documents: List of document dictionaries
            max_tokens: Maximum approximate token count

        Returns:
            Formatted context string
        """
        if max_tokens is None:
            max_tokens = RAGConfig.MAX_CONTEXT_TOKENS

        context_parts = []
        current_length = 0

        for doc in documents:
            text = doc.get('document', '')
            # Rough token estimate (1 token ≈ 4 chars)
            estimated_tokens = len(text) // 4

            if current_length + estimated_tokens > max_tokens:
                break

            collection = doc.get('collection', 'unknown')
            context_parts.append(f"[{collection.upper()}]\n{text}")
            current_length += estimated_tokens

        return "\n\n".join(context_parts)
