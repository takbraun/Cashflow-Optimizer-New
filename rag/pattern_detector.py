"""
Pattern Detector - Detects spending patterns from financial data
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import calendar


class PatternDetector:
    """Detects spending patterns from database records"""

    def __init__(self):
        """
        Initialize pattern detector
        """
        pass

    def detect_recent_patterns(
        self,
        period: str = 'month',
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect patterns in recent spending

        Args:
            period: 'week', 'month', or '3months'
            category: Optional category filter

        Returns:
            List of detected patterns
        """
        from app import VariableExpenseLog

        # Calculate date range
        end_date = datetime.now()
        if period == 'week':
            start_date = end_date - timedelta(days=7)
            compare_start = start_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
            compare_start = start_date - timedelta(days=30)
        else:  # 3months
            start_date = end_date - timedelta(days=90)
            compare_start = start_date - timedelta(days=90)

        # Query current period expenses
        query = VariableExpenseLog.query.filter(
            VariableExpenseLog.expense_date >= start_date.date(),
            VariableExpenseLog.expense_date <= end_date.date()
        )
        if category:
            query = query.filter(VariableExpenseLog.category == category)
        current_expenses = query.all()

        # Query comparison period
        compare_query = VariableExpenseLog.query.filter(
            VariableExpenseLog.expense_date >= compare_start.date(),
            VariableExpenseLog.expense_date < start_date.date()
        )
        if category:
            compare_query = compare_query.filter(VariableExpenseLog.category == category)
        compare_expenses = compare_query.all()

        patterns = []

        # Detect category trends
        category_patterns = self._detect_category_trends(
            current_expenses, compare_expenses
        )
        patterns.extend(category_patterns)

        # Detect spending peaks
        peak_patterns = self._detect_spending_peaks(current_expenses)
        patterns.extend(peak_patterns)

        # Detect day-of-week patterns
        dow_patterns = self._detect_day_of_week_patterns(current_expenses)
        patterns.extend(dow_patterns)

        return patterns

    def _detect_category_trends(
        self,
        current: List,
        previous: List
    ) -> List[Dict]:
        """Detect trends in category spending"""
        patterns = []

        # Sum by category for current period
        current_by_cat = defaultdict(float)
        for exp in current:
            current_by_cat[exp.category or 'Sin categoría'] += exp.amount

        # Sum by category for previous period
        previous_by_cat = defaultdict(float)
        for exp in previous:
            previous_by_cat[exp.category or 'Sin categoría'] += exp.amount

        # Compare
        for cat, current_total in current_by_cat.items():
            previous_total = previous_by_cat.get(cat, 0)

            if previous_total > 0:
                change_pct = ((current_total - previous_total) / previous_total) * 100

                if abs(change_pct) >= 15:  # Significant change threshold
                    pattern_type = 'increase' if change_pct > 0 else 'decrease'
                    severity = 'high' if abs(change_pct) >= 30 else 'moderate'

                    patterns.append({
                        'type': f'category_{pattern_type}',
                        'category': cat,
                        'current_amount': round(current_total, 2),
                        'previous_amount': round(previous_total, 2),
                        'change_percent': round(change_pct, 1),
                        'severity': severity,
                        'description': (
                            f"Los gastos en {cat} {'aumentaron' if change_pct > 0 else 'disminuyeron'} "
                            f"{abs(change_pct):.1f}% (${previous_total:.2f} → ${current_total:.2f})"
                        )
                    })

        return patterns

    def _detect_spending_peaks(self, expenses: List) -> List[Dict]:
        """Detect unusual spending spikes"""
        patterns = []

        if not expenses:
            return patterns

        # Calculate average and std dev
        amounts = [e.amount for e in expenses]
        avg = sum(amounts) / len(amounts)
        variance = sum((x - avg) ** 2 for x in amounts) / len(amounts)
        std_dev = variance ** 0.5

        # Find outliers (> 2 standard deviations)
        threshold = avg + (2 * std_dev)

        for exp in expenses:
            if exp.amount > threshold and exp.amount > 100:  # Min $100 for significance
                exp_date = exp.expense_date
                if isinstance(exp_date, str):
                    exp_date = datetime.fromisoformat(exp_date)

                patterns.append({
                    'type': 'spending_spike',
                    'category': exp.category or 'Sin categoría',
                    'amount': round(exp.amount, 2),
                    'date': exp_date.strftime('%Y-%m-%d'),
                    'average': round(avg, 2),
                    'threshold': round(threshold, 2),
                    'severity': 'high' if exp.amount > threshold * 1.5 else 'moderate',
                    'description': (
                        f"Gasto inusual de ${exp.amount:.2f} en {exp.category or 'Sin categoría'} "
                        f"el {exp_date.strftime('%d/%m')} (promedio: ${avg:.2f})"
                    )
                })

        return patterns

    def _detect_day_of_week_patterns(self, expenses: List) -> List[Dict]:
        """Detect patterns by day of week"""
        patterns = []

        if len(expenses) < 7:  # Need at least a week of data
            return patterns

        # Sum by day of week
        dow_totals = defaultdict(float)
        dow_counts = defaultdict(int)

        for exp in expenses:
            exp_date = exp.expense_date
            if isinstance(exp_date, str):
                exp_date = datetime.fromisoformat(exp_date)

            dow = calendar.day_name[exp_date.weekday()]
            dow_totals[dow] += exp.amount
            dow_counts[dow] += 1

        # Find peak days
        if dow_totals:
            total_avg = sum(dow_totals.values()) / len(dow_totals)

            for dow, total in dow_totals.items():
                if total > total_avg * 1.5:  # 50% above average
                    patterns.append({
                        'type': 'day_of_week_peak',
                        'day': dow,
                        'total': round(total, 2),
                        'count': dow_counts[dow],
                        'average_all_days': round(total_avg, 2),
                        'severity': 'moderate',
                        'description': (
                            f"Los {dow} tienden a tener más gastos "
                            f"(${total:.2f} total, {dow_counts[dow]} transacciones)"
                        )
                    })

        return patterns

    def analyze_daily_spending_pattern(self) -> Dict[str, Any]:
        """
        Analyze spending patterns by day of month

        Returns:
            Dict with daily spending analysis
        """
        from app import VariableExpenseLog

        # Get last 3 months of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        expenses = VariableExpenseLog.query.filter(
            VariableExpenseLog.expense_date >= start_date.date()
        ).all()

        # Sum by day of month
        day_totals = defaultdict(float)
        day_counts = defaultdict(int)

        for exp in expenses:
            exp_date = exp.expense_date
            if isinstance(exp_date, str):
                exp_date = datetime.fromisoformat(exp_date)

            day = exp_date.day
            day_totals[day] += exp.amount
            day_counts[day] += 1

        # Calculate averages
        day_averages = {
            day: total / max(day_counts[day], 1)
            for day, total in day_totals.items()
        }

        # Find low-spending periods (good for savings)
        overall_avg = sum(day_averages.values()) / len(day_averages) if day_averages else 0
        low_spending_days = [
            day for day, avg in day_averages.items()
            if avg < overall_avg * 0.7
        ]

        return {
            'day_averages': day_averages,
            'day_totals': dict(day_totals),
            'low_spending_days': sorted(low_spending_days),
            'overall_daily_average': round(overall_avg, 2),
            'best_days_for_savings': sorted(low_spending_days)[:5]
        }

    def get_category_breakdown(
        self,
        months: int = 3
    ) -> Dict[str, Dict]:
        """
        Get spending breakdown by category

        Args:
            months: Number of months to analyze

        Returns:
            Dict with category statistics
        """
        from app import VariableExpenseLog

        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)

        expenses = VariableExpenseLog.query.filter(
            VariableExpenseLog.expense_date >= start_date.date()
        ).all()

        categories = defaultdict(lambda: {
            'total': 0,
            'count': 0,
            'amounts': [],
            'dates': []
        })

        for exp in expenses:
            cat = exp.category or 'Sin categoría'
            categories[cat]['total'] += exp.amount
            categories[cat]['count'] += 1
            categories[cat]['amounts'].append(exp.amount)

            exp_date = exp.expense_date
            if isinstance(exp_date, str):
                exp_date = datetime.fromisoformat(exp_date)
            categories[cat]['dates'].append(exp_date)

        # Calculate statistics
        result = {}
        for cat, data in categories.items():
            amounts = data['amounts']
            result[cat] = {
                'total': round(data['total'], 2),
                'count': data['count'],
                'average': round(data['total'] / data['count'], 2) if data['count'] > 0 else 0,
                'min': round(min(amounts), 2) if amounts else 0,
                'max': round(max(amounts), 2) if amounts else 0,
                'monthly_average': round(data['total'] / months, 2)
            }

        return result

    def format_patterns_for_llm(self, patterns: List[Dict]) -> str:
        """
        Format detected patterns as text for LLM context

        Args:
            patterns: List of pattern dictionaries

        Returns:
            Formatted text
        """
        if not patterns:
            return "No se detectaron patrones significativos en el período analizado."

        lines = ["Patrones detectados:"]
        for i, pattern in enumerate(patterns, 1):
            lines.append(f"{i}. {pattern.get('description', 'Patrón sin descripción')}")
            if pattern.get('severity') == 'high':
                lines.append("   ⚠️ Requiere atención")

        return "\n".join(lines)
