"""
Document Processor - Converts SQLAlchemy models to vectorizable documents
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
import calendar


class DocumentProcessor:
    """Processes financial data into documents for vector storage"""

    def process_variable_expense(self, expense) -> Dict[str, Any]:
        """
        Convert a VariableExpenseLog to a document

        Args:
            expense: VariableExpenseLog model instance

        Returns:
            Dict with 'id', 'text', and 'metadata'
        """
        # Get card name if available
        card_name = expense.card.name if expense.card else "Efectivo"

        # Format date
        expense_date = expense.expense_date
        if isinstance(expense_date, str):
            expense_date = datetime.fromisoformat(expense_date)

        day_of_week = calendar.day_name[expense_date.weekday()]
        is_weekend = expense_date.weekday() >= 5

        # Build document text
        description = expense.description or "Sin descripción"
        text = (
            f"Gasto de ${expense.amount:.2f} en categoría {expense.category} "
            f"el {expense_date.strftime('%Y-%m-%d')} ({day_of_week}) "
            f"con tarjeta {card_name}. Descripción: {description}"
        )

        # Build metadata
        metadata = {
            "expense_id": expense.id,
            "amount": float(expense.amount),
            "category": expense.category or "Sin categoría",
            "date": expense_date.strftime("%Y-%m-%d"),
            "month": expense_date.strftime("%Y-%m"),
            "day_of_week": day_of_week,
            "day_of_month": expense_date.day,
            "is_weekend": is_weekend,
            "card_id": expense.card_id or 0,
            "card_name": card_name,
            "has_description": bool(expense.description)
        }

        return {
            "id": expense.id,
            "text": text,
            "metadata": metadata
        }

    def process_fixed_expense(self, expense) -> Dict[str, Any]:
        """
        Convert a FixedExpense to a document

        Args:
            expense: FixedExpense model instance

        Returns:
            Dict with 'id', 'text', and 'metadata'
        """
        text = (
            f"Gasto fijo mensual: {expense.name} por ${expense.amount:.2f} "
            f"vence el día {expense.due_day} de cada mes. "
            f"Categoría: {expense.category or 'General'}. "
            f"Estado: {'Activo' if expense.active else 'Inactivo'}"
        )

        metadata = {
            "expense_id": expense.id,
            "name": expense.name,
            "amount": float(expense.amount),
            "due_day": expense.due_day,
            "category": expense.category or "General",
            "active": expense.active,
            "type": "fixed"
        }

        return {
            "id": f"fixed_{expense.id}",
            "text": text,
            "metadata": metadata
        }

    def process_card_payment(self, payment) -> Dict[str, Any]:
        """
        Convert a CardPayment to a document

        Args:
            payment: CardPayment model instance

        Returns:
            Dict with 'id', 'text', and 'metadata'
        """
        card_name = payment.card.name if payment.card else "Desconocida"

        payment_date = payment.payment_date
        if isinstance(payment_date, str):
            payment_date = datetime.fromisoformat(payment_date)

        text = (
            f"Pago de tarjeta {card_name} por ${payment.amount:.2f} "
            f"el {payment_date.strftime('%Y-%m-%d')}. "
            f"Notas: {payment.notes or 'Sin notas'}"
        )

        metadata = {
            "payment_id": payment.id,
            "card_id": payment.card_id,
            "card_name": card_name,
            "amount": float(payment.amount),
            "date": payment_date.strftime("%Y-%m-%d"),
            "month": payment_date.strftime("%Y-%m"),
            "type": "card_payment"
        }

        return {
            "id": f"payment_{payment.id}",
            "text": text,
            "metadata": metadata
        }

    def create_monthly_summary(
        self,
        month: str,
        variable_expenses: List,
        fixed_expenses: List,
        card_payments: List,
        income_schedule,
        checking_balance: float,
        savings_balance: float,
        savings_transferred: float = 0
    ) -> Dict[str, Any]:
        """
        Create a monthly summary document

        Args:
            month: Month string in format 'YYYY-MM'
            variable_expenses: List of VariableExpenseLog for the month
            fixed_expenses: List of FixedExpense
            card_payments: List of CardPayment for the month
            income_schedule: IncomeSchedule model
            checking_balance: Current checking account balance
            savings_balance: Current savings balance
            savings_transferred: Amount transferred to savings this month

        Returns:
            Dict with 'id', 'text', and 'metadata'
        """
        # Calculate totals by category
        category_totals = {}
        total_variable = 0
        for exp in variable_expenses:
            cat = exp.category or "Sin categoría"
            category_totals[cat] = category_totals.get(cat, 0) + exp.amount
            total_variable += exp.amount

        # Fixed expenses total
        total_fixed = sum(e.amount for e in fixed_expenses if e.active)

        # Card payments total
        total_card_payments = sum(p.amount for p in card_payments)

        # Income
        total_income = income_schedule.amount * 2 if income_schedule else 0

        # Top category
        top_category = max(category_totals, key=category_totals.get) if category_totals else "N/A"

        # Build category breakdown text
        category_text = ", ".join(
            f"{cat} (${amt:.2f})" for cat, amt in sorted(
                category_totals.items(), key=lambda x: x[1], reverse=True
            )
        )

        text = (
            f"Resumen financiero de {month}:\n"
            f"- Total gastos variables: ${total_variable:.2f}\n"
            f"- Desglose por categoría: {category_text or 'Sin gastos'}\n"
            f"- Gastos fijos pagados: ${total_fixed:.2f}\n"
            f"- Pagos de tarjetas: ${total_card_payments:.2f}\n"
            f"- Ingresos totales: ${total_income:.2f}\n"
            f"- Balance de cheques: ${checking_balance:.2f}\n"
            f"- Balance de ahorros: ${savings_balance:.2f}\n"
            f"- Transferido a ahorros: ${savings_transferred:.2f}\n"
            f"- Categoría con mayor gasto: {top_category}"
        )

        metadata = {
            "month": month,
            "total_variable": float(total_variable),
            "total_fixed": float(total_fixed),
            "total_card_payments": float(total_card_payments),
            "total_income": float(total_income),
            "checking_balance": float(checking_balance),
            "savings_balance": float(savings_balance),
            "savings_transferred": float(savings_transferred),
            "top_category": top_category,
            "num_variable_expenses": len(variable_expenses),
            "num_categories": len(category_totals),
            "category_totals": category_totals
        }

        return {
            "id": month,
            "text": text,
            "metadata": metadata
        }

    def create_category_summary(
        self,
        category: str,
        expenses: List,
        period: str = "month"
    ) -> Dict[str, Any]:
        """
        Create a summary for a specific category

        Args:
            category: Category name
            expenses: List of expenses in this category
            period: Time period ('week', 'month', '3months')

        Returns:
            Dict with summary information
        """
        if not expenses:
            return {
                "category": category,
                "total": 0,
                "count": 0,
                "average": 0,
                "text": f"No hay gastos en la categoría {category} para el período {period}"
            }

        total = sum(e.amount for e in expenses)
        count = len(expenses)
        average = total / count if count > 0 else 0

        # Find peak days
        day_totals = {}
        for exp in expenses:
            exp_date = exp.expense_date
            if isinstance(exp_date, str):
                exp_date = datetime.fromisoformat(exp_date)
            day_name = calendar.day_name[exp_date.weekday()]
            day_totals[day_name] = day_totals.get(day_name, 0) + exp.amount

        peak_days = sorted(day_totals, key=day_totals.get, reverse=True)[:2]

        text = (
            f"Resumen de categoría {category} ({period}):\n"
            f"- Total gastado: ${total:.2f}\n"
            f"- Número de transacciones: {count}\n"
            f"- Promedio por transacción: ${average:.2f}\n"
            f"- Días con más gastos: {', '.join(peak_days)}"
        )

        return {
            "category": category,
            "total": total,
            "count": count,
            "average": average,
            "peak_days": peak_days,
            "text": text,
            "period": period
        }
