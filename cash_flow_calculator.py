"""
Cash Flow Calculator
Analyzes cash flow and determines available savings
"""

from datetime import datetime, timedelta
from typing import Dict, List
import calendar


class CashFlowCalculator:
    """
    Calculates available funds for savings based on:
    - Current balance
    - Upcoming expenses
    - Income schedule
    - Savings goals
    """
    
    def __init__(self, current_balance: float, income_schedule: any, 
                 savings_goal: any):
        self.current_balance = current_balance
        self.income_schedule = income_schedule
        self.savings_goal = savings_goal
    
    def calculate_available_for_savings(self) -> Dict:
        """
        Calculate how much can be transferred to savings right now.
        
        Uses Polo's Opción C strategy:
        - Maintain minimum comfort balance ($2,000)
        - Reserve funds for upcoming payments
        - Transfer excess to savings
        - Prioritize savings goal per paycheck
        """
        from app import Transaction, FixedExpense
        
        today = datetime.now()
        
        # Determine current paycheck period
        if today.day <= self.income_schedule.first_paycheck_day:
            current_period = 'first'
            next_paycheck = datetime(today.year, today.month, self.income_schedule.first_paycheck_day)
            if next_paycheck < today:
                # Next paycheck is next month
                if today.month == 12:
                    next_paycheck = datetime(today.year + 1, 1, self.income_schedule.first_paycheck_day)
                else:
                    next_paycheck = datetime(today.year, today.month + 1, self.income_schedule.first_paycheck_day)
        else:
            current_period = 'second'
            next_paycheck = datetime(today.year, today.month, self.income_schedule.second_paycheck_day)
            if next_paycheck < today:
                # Next paycheck is next month
                if today.month == 12:
                    next_paycheck = datetime(today.year + 1, 1, self.income_schedule.second_paycheck_day)
                else:
                    next_paycheck = datetime(today.year, today.month + 1, self.income_schedule.second_paycheck_day)
        
        # Calculate expenses until next paycheck
        upcoming_expenses = self._calculate_upcoming_expenses(today, next_paycheck)
        
        # Calculate available
        available = self.current_balance - self.savings_goal.min_balance_comfort - upcoming_expenses
        
        # Don't transfer more than savings goal
        recommended_transfer = min(available, self.savings_goal.amount_per_paycheck)
        
        # Don't allow negative transfers
        recommended_transfer = max(0, recommended_transfer)
        
        return {
            'current_balance': self.current_balance,
            'min_balance_required': self.savings_goal.min_balance_comfort,
            'upcoming_expenses': upcoming_expenses,
            'available_for_savings': available,
            'recommended_transfer': recommended_transfer,
            'savings_goal_per_paycheck': self.savings_goal.amount_per_paycheck,
            'would_meet_goal': recommended_transfer >= self.savings_goal.amount_per_paycheck,
            'next_paycheck_date': next_paycheck.strftime('%Y-%m-%d'),
            'current_period': current_period
        }
    
    def _calculate_upcoming_expenses(self, start: datetime, end: datetime) -> float:
        """Calculate total expenses between two dates."""
        from app import Transaction, FixedExpense
        
        total = 0.0
        
        # Card payments scheduled in this period
        payments = Transaction.query.filter(
            Transaction.payment_date >= start,
            Transaction.payment_date <= end
        ).all()
        
        for payment in payments:
            total += payment.amount
        
        # Fixed expenses due in this period
        fixed_expenses = FixedExpense.query.filter_by(active=True).all()
        
        for expense in fixed_expenses:
            # Check if due date falls in period
            if self._is_due_in_period(expense.due_day, start, end):
                total += expense.amount
        
        # Variable expenses (prorated)
        days_in_period = (end - start).days
        variable_daily = self.savings_goal.variable_expenses_monthly / 30
        total += (variable_daily * days_in_period)
        
        return total
    
    def _is_due_in_period(self, due_day: int, start: datetime, end: datetime) -> bool:
        """Check if a monthly expense due day falls within a period."""
        current = start
        while current <= end:
            if current.day == due_day:
                return True
            current += timedelta(days=1)
        return False
    
    def project_savings_timeline(self, months: int = 12) -> List[Dict]:
        """
        Project savings growth over time.
        
        Returns list of monthly projections showing:
        - Month
        - Starting balance
        - Income
        - Expenses
        - Savings added
        - Ending balance
        """
        from app import SavingsAccount, BonusEvent
        
        savings = SavingsAccount.query.first()
        current_savings = savings.balance if savings else 0
        current_checking = self.current_balance
        
        projections = []
        current_date = datetime.now()
        
        for month_offset in range(months):
            # Calculate month
            month_date = current_date + timedelta(days=30 * month_offset)
            
            # Income for month (2 paychecks)
            monthly_income = self.income_schedule.amount * 2
            
            # Expenses for month
            from app import FixedExpense
            fixed_expenses = FixedExpense.query.filter_by(active=True).all()
            fixed_total = sum(e.amount for e in fixed_expenses)
            variable_total = self.savings_goal.variable_expenses_monthly
            
            # Credit card payments (estimate from current balances)
            # This is simplified - in production would project actual transactions
            from app import Card
            cards = Card.query.filter_by(active=True).all()
            card_payments = sum(c.current_balance for c in cards)
            
            monthly_expenses = fixed_total + variable_total + card_payments
            
            # Check for bonus
            bonus = 0
            bonus_events = BonusEvent.query.filter(
                BonusEvent.received == False
            ).all()
            for event in bonus_events:
                if event.expected_date.year == month_date.year and \
                   event.expected_date.month == month_date.month:
                    bonus = event.amount
            
            # Savings for month
            net_monthly = monthly_income + bonus - monthly_expenses
            monthly_savings = min(
                net_monthly - self.savings_goal.min_balance_comfort,
                self.savings_goal.amount_per_paycheck * 2
            )
            monthly_savings = max(0, monthly_savings)
            
            # Update balances
            current_savings += monthly_savings
            current_checking = current_checking + monthly_income + bonus - monthly_expenses - monthly_savings
            
            projections.append({
                'month': month_date.strftime('%b %Y'),
                'income': monthly_income + bonus,
                'bonus': bonus,
                'expenses': monthly_expenses,
                'savings_added': monthly_savings,
                'savings_balance': current_savings,
                'checking_balance': current_checking,
                'target_reached': current_savings >= savings.target if savings else False
            })
        
        return projections
    
    def analyze_paycheck_period(self, period: str) -> Dict:
        """
        Analyze a specific paycheck period (first or second half of month).
        
        Returns breakdown of:
        - Income
        - Fixed expenses
        - Variable expenses  
        - Card payments
        - Available for savings
        """
        from app import FixedExpense, Transaction
        
        today = datetime.now()
        
        # Determine period dates
        if period == 'first':
            start = datetime(today.year, today.month, 1)
            end = datetime(today.year, today.month, self.income_schedule.first_paycheck_day)
        else:
            start = datetime(today.year, today.month, self.income_schedule.first_paycheck_day + 1)
            # End of month
            last_day = calendar.monthrange(today.year, today.month)[1]
            end = datetime(today.year, today.month, last_day)
        
        # Income in period
        income = self.income_schedule.amount
        
        # Fixed expenses in period
        fixed_expenses = FixedExpense.query.filter_by(active=True).all()
        fixed_in_period = sum(
            e.amount for e in fixed_expenses 
            if self._is_due_in_period(e.due_day, start, end)
        )
        
        # Variable expenses (half month)
        variable_in_period = self.savings_goal.variable_expenses_monthly / 2
        
        # Card payments in period
        card_payments = Transaction.query.filter(
            Transaction.payment_date >= start,
            Transaction.payment_date <= end
        ).all()
        card_total = sum(p.amount for p in card_payments)
        
        # Calculate available
        total_expenses = fixed_in_period + variable_in_period + card_total
        available = income - total_expenses
        
        return {
            'period': period,
            'start_date': start.strftime('%Y-%m-%d'),
            'end_date': end.strftime('%Y-%m-%d'),
            'income': income,
            'expenses': {
                'fixed': fixed_in_period,
                'variable': variable_in_period,
                'cards': card_total,
                'total': total_expenses
            },
            'available_for_savings': max(0, available),
            'meets_savings_goal': available >= self.savings_goal.amount_per_paycheck
        }
