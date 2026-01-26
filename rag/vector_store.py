"""
Vector Store - Simple vector storage using sentence-transformers and numpy
Compatible with Python 3.14 without ChromaDB
"""

import json
import os
import numpy as np
from typing import List, Dict, Optional, Any
from pathlib import Path
from sentence_transformers import SentenceTransformer
from .config import RAGConfig


class FinancialVectorStore:
    """
    Simple vector store implementation using sentence-transformers and numpy.
    Stores vectors in JSON files for persistence.
    """

    def __init__(self, persist_directory: str = None):
        """Initialize vector store with persistence"""
        self.persist_dir = Path(persist_directory or RAGConfig.CHROMA_PERSIST_DIR)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # Initialize sentence transformer model
        self._model = None

        # Collections storage
        self.collections = {
            'expenses': {'documents': [], 'embeddings': [], 'metadatas': [], 'ids': []},
            'summaries': {'documents': [], 'embeddings': [], 'metadatas': [], 'ids': []},
            'patterns': {'documents': [], 'embeddings': [], 'metadatas': [], 'ids': []}
        }

        # Load existing data
        self._load_all()

    @property
    def model(self):
        """Lazy load the embedding model"""
        if self._model is None:
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._model

    def _get_collection_path(self, name: str) -> Path:
        """Get path for collection file"""
        return self.persist_dir / f"{name}.json"

    def _load_collection(self, name: str):
        """Load collection from disk"""
        path = self._get_collection_path(name)
        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)
                self.collections[name] = {
                    'documents': data.get('documents', []),
                    'embeddings': [np.array(e) for e in data.get('embeddings', [])],
                    'metadatas': data.get('metadatas', []),
                    'ids': data.get('ids', [])
                }

    def _save_collection(self, name: str):
        """Save collection to disk"""
        path = self._get_collection_path(name)
        data = {
            'documents': self.collections[name]['documents'],
            'embeddings': [e.tolist() for e in self.collections[name]['embeddings']],
            'metadatas': self.collections[name]['metadatas'],
            'ids': self.collections[name]['ids']
        }
        with open(path, 'w') as f:
            json.dump(data, f)

    def _load_all(self):
        """Load all collections"""
        for name in self.collections:
            self._load_collection(name)

    def _save_all(self):
        """Save all collections"""
        for name in self.collections:
            self._save_collection(name)

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def _add_document(self, collection: str, doc_id: str, text: str, metadata: Dict):
        """Add or update a document in a collection"""
        col = self.collections[collection]

        # Generate embedding
        embedding = self.model.encode(text)

        # Check if document exists
        if doc_id in col['ids']:
            idx = col['ids'].index(doc_id)
            col['documents'][idx] = text
            col['embeddings'][idx] = embedding
            col['metadatas'][idx] = metadata
        else:
            col['ids'].append(doc_id)
            col['documents'].append(text)
            col['embeddings'].append(embedding)
            col['metadatas'].append(metadata)

        # Persist
        self._save_collection(collection)

    def _query_collection(
        self,
        collection: str,
        query: str,
        n_results: int = 10,
        where: Optional[Dict] = None
    ) -> Dict:
        """Query a collection with semantic search"""
        col = self.collections[collection]

        if not col['documents']:
            return {'documents': [[]], 'metadatas': [[]], 'ids': [[]], 'distances': [[]]}

        # Generate query embedding
        query_embedding = self.model.encode(query)

        # Calculate similarities
        similarities = []
        for i, emb in enumerate(col['embeddings']):
            # Apply metadata filter if specified
            if where:
                meta = col['metadatas'][i]
                match = all(meta.get(k) == v for k, v in where.items())
                if not match:
                    continue

            sim = self._cosine_similarity(query_embedding, emb)
            similarities.append((i, sim))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Get top results
        top_results = similarities[:n_results]

        documents = []
        metadatas = []
        ids = []
        distances = []

        for idx, sim in top_results:
            documents.append(col['documents'][idx])
            metadatas.append(col['metadatas'][idx])
            ids.append(col['ids'][idx])
            distances.append(1 - sim)  # Convert similarity to distance

        return {
            'documents': [documents],
            'metadatas': [metadatas],
            'ids': [ids],
            'distances': [distances]
        }

    # Public API methods

    def add_expense(self, expense_id: int, text: str, metadata: Dict[str, Any]) -> None:
        """Add a single expense document"""
        doc_id = f"expense_{expense_id}"
        self._add_document('expenses', doc_id, text, metadata)

    def add_expenses_batch(self, expenses: List[Dict]) -> None:
        """Add multiple expense documents in batch"""
        for e in expenses:
            doc_id = f"expense_{e['id']}"
            self._add_document('expenses', doc_id, e['text'], e['metadata'])

    def add_summary(self, month: str, text: str, metadata: Dict[str, Any]) -> None:
        """Add or update a monthly summary"""
        doc_id = f"summary_{month}"
        self._add_document('summaries', doc_id, text, metadata)

    def add_pattern(self, pattern_id: str, text: str, metadata: Dict[str, Any]) -> None:
        """Add a detected pattern"""
        self._add_document('patterns', pattern_id, text, metadata)

    def query_expenses(
        self,
        query: str,
        n_results: int = 10,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None
    ) -> Dict:
        """Query expense documents by semantic similarity"""
        return self._query_collection('expenses', query, n_results, where)

    def query_summaries(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> Dict:
        """Query monthly summaries"""
        return self._query_collection('summaries', query, n_results, where)

    def query_patterns(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> Dict:
        """Query detected patterns"""
        return self._query_collection('patterns', query, n_results, where)

    def query_all(
        self,
        query: str,
        n_results: int = 5
    ) -> Dict[str, Dict]:
        """Query all collections and combine results"""
        return {
            'expenses': self.query_expenses(query, n_results),
            'summaries': self.query_summaries(query, n_results),
            'patterns': self.query_patterns(query, n_results)
        }

    def get_expense_by_id(self, expense_id: int) -> Optional[Dict]:
        """Get a specific expense document"""
        doc_id = f"expense_{expense_id}"
        col = self.collections['expenses']
        if doc_id in col['ids']:
            idx = col['ids'].index(doc_id)
            return {
                'id': col['ids'][idx],
                'document': col['documents'][idx],
                'metadata': col['metadatas'][idx]
            }
        return None

    def delete_expense(self, expense_id: int) -> None:
        """Delete an expense document"""
        doc_id = f"expense_{expense_id}"
        col = self.collections['expenses']
        if doc_id in col['ids']:
            idx = col['ids'].index(doc_id)
            col['ids'].pop(idx)
            col['documents'].pop(idx)
            col['embeddings'].pop(idx)
            col['metadatas'].pop(idx)
            self._save_collection('expenses')

    def get_collection_stats(self) -> Dict[str, int]:
        """Get document counts for all collections"""
        return {
            name: len(col['documents'])
            for name, col in self.collections.items()
        }

    def clear_all(self) -> None:
        """Clear all collections (use with caution)"""
        for name in self.collections:
            self.collections[name] = {
                'documents': [], 'embeddings': [], 'metadatas': [], 'ids': []
            }
            # Remove file
            path = self._get_collection_path(name)
            if path.exists():
                path.unlink()
