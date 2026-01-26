"""
Insights Engine - Main orchestrator for the RAG system
Simplified version that doesn't directly query SQLAlchemy
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

from .config import RAGConfig
from .vector_store import FinancialVectorStore
from .document_processor import DocumentProcessor
from .retriever import FinancialRetriever
from .generator import InsightGenerator


class InsightsEngine:
    """
    Main orchestrator for the RAG financial insights system.
    This version doesn't query SQLAlchemy directly - data must be passed in.
    """

    def __init__(self):
        """Initialize the insights engine"""
        self.vector_store = FinancialVectorStore()
        self.document_processor = DocumentProcessor()
        self.retriever = FinancialRetriever(self.vector_store)
        self.generator = InsightGenerator()

    def is_configured(self) -> bool:
        """Check if the RAG system is properly configured"""
        return RAGConfig.validate() and self.generator.is_available()

    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            'configured': self.is_configured(),
            'config': RAGConfig.get_status(),
            'collections': self.vector_store.get_collection_stats(),
            'generator_available': self.generator.is_available(),
            'usage': self.generator.get_usage_stats() if self.generator.is_available() else None
        }

    # =========================================================================
    # INDEXING METHODS
    # =========================================================================

    def index_expense(self, expense) -> bool:
        """
        Index a single expense in the vector store

        Args:
            expense: VariableExpenseLog model instance

        Returns:
            True if successful
        """
        try:
            doc = self.document_processor.process_variable_expense(expense)
            self.vector_store.add_expense(
                expense_id=doc['id'],
                text=doc['text'],
                metadata=doc['metadata']
            )
            return True
        except Exception as e:
            print(f"Error indexing expense: {e}")
            return False

    def index_expenses_batch(self, expenses: List) -> Dict[str, int]:
        """
        Index multiple expenses

        Args:
            expenses: List of VariableExpenseLog instances

        Returns:
            Dict with counts
        """
        indexed = 0
        errors = 0

        for expense in expenses:
            try:
                doc = self.document_processor.process_variable_expense(expense)
                self.vector_store.add_expense(
                    expense_id=doc['id'],
                    text=doc['text'],
                    metadata=doc['metadata']
                )
                indexed += 1
            except Exception as e:
                print(f"Error indexing expense {expense.id}: {e}")
                errors += 1

        return {'indexed': indexed, 'errors': errors}

    def update_monthly_summary(
        self,
        month: str,
        variable_expenses: List,
        fixed_expenses: List,
        card_payments: List,
        income_amount: float,
        checking_balance: float,
        savings_balance: float
    ) -> bool:
        """
        Update monthly summary in vector store

        Args:
            month: Month string (YYYY-MM)
            variable_expenses: List of expense dicts or objects
            fixed_expenses: List of fixed expense dicts or objects
            card_payments: List of card payment dicts or objects
            income_amount: Monthly income amount
            checking_balance: Current checking balance
            savings_balance: Current savings balance
        """
        try:
            # Calculate totals
            total_variable = sum(
                e.amount if hasattr(e, 'amount') else e.get('amount', 0)
                for e in variable_expenses
            )

            total_fixed = sum(
                e.amount if hasattr(e, 'amount') else e.get('amount', 0)
                for e in fixed_expenses
            )

            total_card_payments = sum(
                p.amount if hasattr(p, 'amount') else p.get('amount', 0)
                for p in card_payments
            )

            # Category breakdown
            category_totals = {}
            for exp in variable_expenses:
                cat = exp.category if hasattr(exp, 'category') else exp.get('category', 'Otros')
                amt = exp.amount if hasattr(exp, 'amount') else exp.get('amount', 0)
                category_totals[cat] = category_totals.get(cat, 0) + amt

            top_category = max(category_totals, key=category_totals.get) if category_totals else "N/A"

            category_text = ", ".join(
                f"{cat} (${amt:.2f})" for cat, amt in sorted(
                    category_totals.items(), key=lambda x: x[1], reverse=True
                )
            )

            text = (
                f"Resumen financiero de {month}:\n"
                f"- Total gastos variables: ${total_variable:.2f}\n"
                f"- Desglose por categoría: {category_text or 'Sin gastos'}\n"
                f"- Gastos fijos: ${total_fixed:.2f}\n"
                f"- Pagos de tarjetas: ${total_card_payments:.2f}\n"
                f"- Ingresos totales: ${income_amount:.2f}\n"
                f"- Balance de cheques: ${checking_balance:.2f}\n"
                f"- Balance de ahorros: ${savings_balance:.2f}\n"
                f"- Categoría con mayor gasto: {top_category}"
            )

            metadata = {
                "month": month,
                "total_variable": float(total_variable),
                "total_fixed": float(total_fixed),
                "total_card_payments": float(total_card_payments),
                "total_income": float(income_amount),
                "checking_balance": float(checking_balance),
                "savings_balance": float(savings_balance),
                "top_category": top_category
            }

            self.vector_store.add_summary(month=month, text=text, metadata=metadata)
            return True

        except Exception as e:
            print(f"Error updating monthly summary: {e}")
            return False

    # =========================================================================
    # ANALYSIS METHODS (use only vector store + LLM, no SQLAlchemy)
    # =========================================================================

    def analyze_spending(
        self,
        period: str = 'month',
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze spending using vector store data

        Args:
            period: 'week', 'month', or '3months'
            category: Optional category filter

        Returns:
            Analysis results
        """
        # Build query
        query = f"gastos del último {period}"
        if category:
            query += f" en categoría {category}"

        # Get relevant context from vector store
        context_docs = self.retriever.get_relevant_context(
            query=query,
            collections=['expenses', 'summaries', 'patterns'],
            top_k=15
        )

        context = self.retriever.format_context_for_llm(context_docs)

        if not context.strip():
            return {
                'analysis': 'No hay suficientes datos indexados para analizar. Usa el botón de reindexar primero.',
                'patterns_detected': [],
                'sources_count': 0,
                'period': period,
                'category': category,
                'error': False
            }

        # Generate analysis
        result = self.generator.analyze_spending(
            context=context,
            patterns="Basado en los datos del vector store",
            query=f"Analiza mis gastos del último {period}" + (f" en {category}" if category else "")
        )

        return {
            'analysis': result.get('text', ''),
            'patterns_detected': [],
            'sources_count': len(context_docs),
            'period': period,
            'category': category,
            'error': result.get('error', False),
            'usage': result.get('usage', {})
        }

    def get_optimization_suggestions(
        self,
        category_data: Dict[str, float] = None,
        savings_goal: float = 500,
        min_balance: float = 2000
    ) -> Dict[str, Any]:
        """
        Get optimization suggestions

        Args:
            category_data: Dict of category -> total amount
            savings_goal: Target savings per paycheck
            min_balance: Minimum comfort balance
        """
        # Get context from vector store
        context_docs = self.retriever.get_relevant_context(
            query="optimización de gastos y ahorro sugerencias",
            collections=['summaries', 'patterns', 'expenses'],
            top_k=10
        )
        context = self.retriever.format_context_for_llm(context_docs)

        # Format category data if provided
        if category_data:
            category_text = "\n".join(
                f"- {cat}: ${amt:.2f}" for cat, amt in sorted(
                    category_data.items(), key=lambda x: x[1], reverse=True
                )
            )
        else:
            category_text = "Sin datos de categorías disponibles"

        result = self.generator.get_optimization_suggestions(
            category_data=category_text,
            context=context,
            savings_goal=savings_goal,
            min_balance=min_balance
        )

        return {
            'suggestions': result.get('text', ''),
            'category_breakdown': category_data or {},
            'error': result.get('error', False),
            'usage': result.get('usage', {})
        }

    def get_best_savings_time(
        self,
        checking_balance: float = 0,
        savings_goal: float = 500,
        first_paycheck_day: int = 9,
        second_paycheck_day: int = 23,
        pending_expenses: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Get best time to transfer to savings

        Args:
            checking_balance: Current checking balance
            savings_goal: Target savings per paycheck
            first_paycheck_day: Day of first paycheck
            second_paycheck_day: Day of second paycheck
            pending_expenses: List of pending fixed expenses
        """
        pending_text = ""
        if pending_expenses:
            pending_text = "\n".join(
                f"- {exp.get('name', 'Gasto')}: ${exp.get('amount', 0):.2f} (día {exp.get('due_day', '?')})"
                for exp in pending_expenses
            )

        result = self.generator.generate_insight(
            template='BEST_SAVINGS_TIME',
            context="",
            daily_patterns="Basado en historial de gastos",
            pending_obligations=pending_text or "Sin obligaciones pendientes especificadas",
            first_paycheck=first_paycheck_day,
            second_paycheck=second_paycheck_day,
            checking_balance=checking_balance,
            savings_goal=savings_goal
        )

        return {
            'recommendation': result.get('text', ''),
            'best_days': [],
            'daily_averages': {},
            'error': result.get('error', False),
            'usage': result.get('usage', {})
        }

    def get_category_insight(self, category: str) -> Dict[str, Any]:
        """
        Get insight for a specific category using vector store only
        """
        # Get history from vector store
        history_docs = self.retriever.get_expense_history(category=category, top_k=20)
        history_text = "\n".join(
            doc.get('document', '') for doc in history_docs[:10]
        )

        if not history_text:
            return {
                'category': category,
                'insight': f"No se encontraron datos de gastos en la categoría {category} en el índice.",
                'error': False
            }

        # Get patterns
        patterns = self.retriever.get_patterns_for_category(category)
        patterns_text = "\n".join(p.get('document', '') for p in patterns)

        result = self.generator.generate_insight(
            template='CATEGORY_INSIGHT',
            context=patterns_text or "Sin patrones previos",
            category=category,
            category_data=f"Datos de {category} del vector store",
            history=history_text
        )

        return {
            'category': category,
            'insight': result.get('text', ''),
            'data': {},
            'error': result.get('error', False),
            'usage': result.get('usage', {})
        }

    def detect_anomalies(self) -> Dict[str, Any]:
        """
        Detect anomalies using vector store data only
        """
        # Get recent expenses from vector store
        context_docs = self.retriever.get_relevant_context(
            query="gastos inusuales anomalías picos altos",
            collections=['expenses', 'patterns'],
            top_k=15
        )
        context = self.retriever.format_context_for_llm(context_docs)

        if not context.strip():
            return {
                'anomalies': [],
                'explanation': 'No hay suficientes datos indexados para detectar anomalías.',
                'error': False
            }

        result = self.generator.explain_anomalies(
            anomalies="Analiza los gastos y detecta cualquier anomalía",
            context=context
        )

        return {
            'anomalies': [],
            'explanation': result.get('text', ''),
            'error': result.get('error', False),
            'usage': result.get('usage', {})
        }

    def chat(
        self,
        message: str,
        conversation_history: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Chat interface - uses only vector store and LLM

        Args:
            message: User's message
            conversation_history: Previous messages

        Returns:
            Response and metadata
        """
        # Get relevant context from vector store
        context_docs = self.retriever.get_relevant_context(
            query=message,
            collections=['expenses', 'summaries', 'patterns'],
            top_k=10
        )
        context = self.retriever.format_context_for_llm(context_docs)

        result = self.generator.chat_completion(
            message=message,
            context=context if context.strip() else "No hay datos financieros indexados aún.",
            conversation_history=conversation_history
        )

        return {
            'response': result.get('text', ''),
            'sources_used': len(context_docs),
            'error': result.get('error', False),
            'usage': result.get('usage', {})
        }

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def clear_all_data(self) -> bool:
        """Clear all vector store data"""
        try:
            self.vector_store.clear_all()
            return True
        except Exception as e:
            print(f"Error clearing data: {e}")
            return False
