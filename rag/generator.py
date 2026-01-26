"""
Insight Generator - Generates responses using Claude API
"""

from typing import Dict, List, Optional, Any
from anthropic import Anthropic
from .config import RAGConfig
from . import prompt_templates


class InsightGenerator:
    """Generates financial insights using Claude API"""

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the generator with Anthropic client

        Args:
            api_key: Anthropic API key (defaults to config)
            model: Model to use (defaults to config)
        """
        self.api_key = api_key or RAGConfig.ANTHROPIC_API_KEY
        self.model = model or RAGConfig.DEFAULT_MODEL

        if self.api_key:
            self.client = Anthropic(api_key=self.api_key)
        else:
            self.client = None

        # Usage tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def is_available(self) -> bool:
        """Check if the generator is properly configured"""
        return self.client is not None and bool(self.api_key)

    def generate_insight(
        self,
        template: str,
        context: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate an insight using a prompt template

        Args:
            template: Name of the template to use
            context: Retrieved context to include
            **kwargs: Variables to fill in the template

        Returns:
            Dict with 'text', 'usage', and any extracted data
        """
        if not self.is_available():
            return {
                'text': "El sistema RAG no está configurado. Por favor configura ANTHROPIC_API_KEY.",
                'error': True,
                'usage': {'input_tokens': 0, 'output_tokens': 0}
            }

        # Get the template
        template_map = {
            'SPENDING_ANALYSIS': prompt_templates.SPENDING_ANALYSIS_PROMPT,
            'OPTIMIZATION_SUGGESTIONS': prompt_templates.OPTIMIZATION_SUGGESTIONS_PROMPT,
            'BEST_SAVINGS_TIME': prompt_templates.BEST_SAVINGS_TIME_PROMPT,
            'CATEGORY_INSIGHT': prompt_templates.CATEGORY_INSIGHT_PROMPT,
            'ANOMALY_EXPLANATION': prompt_templates.ANOMALY_EXPLANATION_PROMPT,
            'CHAT_RESPONSE': prompt_templates.CHAT_RESPONSE_PROMPT,
            'PATTERN_DETECTION': prompt_templates.PATTERN_DETECTION_PROMPT
        }

        prompt_template = template_map.get(template)
        if not prompt_template:
            return {
                'text': f"Template '{template}' no encontrado.",
                'error': True,
                'usage': {'input_tokens': 0, 'output_tokens': 0}
            }

        # Fill in the template
        try:
            # Add context to kwargs
            kwargs['context'] = context
            prompt = prompt_template.format(**kwargs)
        except KeyError as e:
            return {
                'text': f"Falta variable en template: {e}",
                'error': True,
                'usage': {'input_tokens': 0, 'output_tokens': 0}
            }

        # Call Claude API
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=RAGConfig.MAX_OUTPUT_TOKENS,
                system=prompt_templates.SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Track usage
            self.total_input_tokens += response.usage.input_tokens
            self.total_output_tokens += response.usage.output_tokens

            return {
                'text': response.content[0].text,
                'error': False,
                'usage': {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens
                },
                'model': response.model,
                'stop_reason': response.stop_reason
            }

        except Exception as e:
            return {
                'text': f"Error al generar insight: {str(e)}",
                'error': True,
                'usage': {'input_tokens': 0, 'output_tokens': 0}
            }

    def chat_completion(
        self,
        message: str,
        context: str = "",
        conversation_history: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate a conversational response

        Args:
            message: User's message
            context: Retrieved financial context
            conversation_history: Previous messages in conversation

        Returns:
            Dict with response and metadata
        """
        if not self.is_available():
            return {
                'text': "El sistema RAG no está configurado. Por favor configura ANTHROPIC_API_KEY.",
                'error': True
            }

        # Build messages array
        messages = []

        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history[-5:]:  # Last 5 messages
                messages.append({
                    "role": msg.get('role', 'user'),
                    "content": msg.get('content', '')
                })

        # Format history for template
        history_text = ""
        if conversation_history:
            history_text = "\n".join(
                f"{'Usuario' if m.get('role') == 'user' else 'Asistente'}: {m.get('content', '')}"
                for m in conversation_history[-3:]
            )

        # Generate response using template
        return self.generate_insight(
            template='CHAT_RESPONSE',
            context=context,
            message=message,
            conversation_history=history_text or "Sin historial previo"
        )

    def analyze_spending(
        self,
        context: str,
        patterns: str = "",
        query: str = "Analiza mis gastos recientes"
    ) -> Dict[str, Any]:
        """
        Generate spending analysis

        Args:
            context: Retrieved expense context
            patterns: Detected patterns
            query: User's specific question

        Returns:
            Analysis result
        """
        return self.generate_insight(
            template='SPENDING_ANALYSIS',
            context=context,
            patterns=patterns or "No se detectaron patrones específicos",
            query=query
        )

    def get_optimization_suggestions(
        self,
        category_data: str,
        context: str,
        savings_goal: float,
        min_balance: float
    ) -> Dict[str, Any]:
        """
        Generate optimization suggestions

        Args:
            category_data: Spending by category
            context: Historical context
            savings_goal: User's savings goal
            min_balance: Minimum comfort balance

        Returns:
            Suggestions result
        """
        return self.generate_insight(
            template='OPTIMIZATION_SUGGESTIONS',
            context=context,
            category_data=category_data,
            savings_goal=savings_goal,
            min_balance=min_balance
        )

    def explain_anomalies(
        self,
        anomalies: str,
        context: str
    ) -> Dict[str, Any]:
        """
        Explain detected anomalies

        Args:
            anomalies: List of anomalies found
            context: Historical context

        Returns:
            Explanation result
        """
        return self.generate_insight(
            template='ANOMALY_EXPLANATION',
            context=context,
            anomalies=anomalies
        )

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get cumulative usage statistics"""
        # Approximate cost calculation (based on Claude 3 Haiku pricing)
        input_cost = (self.total_input_tokens / 1_000_000) * 0.25
        output_cost = (self.total_output_tokens / 1_000_000) * 1.25
        total_cost = input_cost + output_cost

        return {
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'estimated_cost_usd': round(total_cost, 4),
            'model': self.model
        }

    def reset_usage_stats(self):
        """Reset usage counters"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
