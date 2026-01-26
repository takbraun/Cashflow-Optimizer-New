"""
Card Recommendation Engine
Intelligent scoring system to recommend best card for purchases
"""

from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional
import calendar


@dataclass
class CardScore:
    """Result of card scoring"""
    card: any  # Card model
    total_score: float
    timing_score: float
    liquidity_score: float
    savings_impact_score: float
    utilization_score: float
    distribution_score: float
    payment_date: datetime
    projected_balance: float
    reasoning: str
    rank: int = 0
    
    def to_dict(self):
        return {
            'card_id': self.card.id,
            'card_name': self.card.name,
            'score': round(self.total_score, 1),
            'breakdown': {
                'timing': round(self.timing_score, 1),
                'liquidity': round(self.liquidity_score, 1),
                'savings_impact': round(self.savings_impact_score, 1),
                'utilization': round(self.utilization_score, 1),
                'distribution': round(self.distribution_score, 1)
            },
            'payment_date': self.payment_date.strftime('%Y-%m-%d'),
            'projected_balance': round(self.projected_balance, 2),
            'reasoning': self.reasoning,
            'rank': self.rank
        }


class CardRecommendationEngine:
    """
    Intelligent card recommendation engine.
    
    Scoring weights:
    - Timing: 35% - When will you pay
    - Liquidity: 25% - Will you have enough cash
    - Savings Impact: 15% - Impact on savings goal
    - Utilization: 15% - Credit utilization
    - Distribution: 10% - Balance transactions across cards
    """
    
    WEIGHTS = {
        'timing': 0.35,
        'liquidity': 0.25,
        'savings_impact': 0.15,
        'utilization': 0.15,
        'distribution': 0.10
    }
    
    def __init__(self, cards: List, current_balance: float, 
                 income_schedule: any, savings_goal: any):
        self.cards = cards
        self.current_balance = current_balance
        self.income_schedule = income_schedule
        self.savings_goal = savings_goal
        
    def recommend(self, purchase_amount: float, 
                  purchase_date: datetime = None,
                  is_deferred: bool = False,
                  num_payments: int = None,
                  payment_frequency: str = None) -> dict:
        """
        Return comprehensive recommendation with liquidity analysis.
        
        Args:
            purchase_amount: Total purchase amount
            purchase_date: When the purchase will be made
            is_deferred: Whether payment is deferred
            num_payments: Number of installments
            payment_frequency: 'weekly', 'biweekly', or 'monthly'
            
        Returns:
            dict with:
                - can_afford_now: bool
                - suggested_wait_date: datetime or None
                - recommendations: List[CardScore]
                - liquidity_analysis: dict
                - deferred_schedule: dict or None
        """
        if not purchase_date:
            purchase_date = datetime.now()
            
        # Calculate payment per installment if deferred
        payment_per_installment = purchase_amount
        if is_deferred and num_payments:
            payment_per_installment = purchase_amount / num_payments
        
        # 1. Check current liquidity
        liquidity_check = self._check_liquidity(
            purchase_amount, 
            purchase_date,
            is_deferred,
            payment_per_installment,
            num_payments,
            payment_frequency
        )
        
        # 2. Score all cards
        recommendations = []
        
        for card in self.cards:
            score = self._calculate_score(
                card, 
                purchase_amount,
                purchase_date,
                is_deferred,
                payment_per_installment,
                num_payments,
                payment_frequency
            )
            recommendations.append(score)
        
        # Sort by score (descending)
        recommendations.sort(key=lambda x: x.total_score, reverse=True)
        
        # Assign ranks
        for i, rec in enumerate(recommendations, 1):
            rec.rank = i
        
        # 3. Build deferred payment schedule if applicable
        deferred_schedule = None
        if is_deferred and recommendations:
            best_card = recommendations[0].card
            deferred_schedule = self._build_payment_schedule(
                best_card,
                purchase_date,
                payment_per_installment,
                num_payments,
                payment_frequency
            )
        
        return {
            'can_afford_now': liquidity_check['can_afford'],
            'suggested_wait_date': liquidity_check.get('suggested_date'),
            'recommendations': recommendations,
            'liquidity_analysis': liquidity_check,
            'deferred_schedule': deferred_schedule
        }
    
    def _calculate_score(self, card: any, amount: float, 
                        purchase_date: datetime,
                        is_deferred: bool = False,
                        payment_per_installment: float = None,
                        num_payments: int = None,
                        payment_frequency: str = None) -> CardScore:
        """Calculate total score for a card."""
        
        # 1. Calculate payment date (for first payment)
        payment_date = self._calculate_payment_date(card, purchase_date)
        
        # 2. Project balance on payment date
        projected_balance = self._project_balance(payment_date)
        
        # 3. Determine amount that affects this payment cycle
        amount_this_cycle = amount
        if is_deferred and payment_per_installment:
            payments_before_first = self._count_payments_before_date(
                purchase_date,
                payment_date,
                payment_frequency
            )
            amount_this_cycle = payment_per_installment * max(1, payments_before_first)
        
        # 4. Calculate component scores
        timing = self._timing_score(purchase_date, payment_date, projected_balance)
        liquidity = self._liquidity_score(projected_balance, amount_this_cycle)
        savings = self._savings_impact_score(payment_date, amount_this_cycle)
        utilization = self._utilization_score(card, amount)
        distribution = self._distribution_score(card)
        
        # 5. Calculate weighted total
        total = (
            timing * self.WEIGHTS['timing'] +
            liquidity * self.WEIGHTS['liquidity'] +
            savings * self.WEIGHTS['savings_impact'] +
            utilization * self.WEIGHTS['utilization'] +
            distribution * self.WEIGHTS['distribution']
        )
        
        # 6. Generate reasoning
        reasoning = self._generate_reasoning(
            card, amount, payment_date, projected_balance, timing, liquidity, savings
        )
        
        return CardScore(
            card=card,
            total_score=total,
            timing_score=timing,
            liquidity_score=liquidity,
            savings_impact_score=savings,
            utilization_score=utilization,
            distribution_score=distribution,
            payment_date=payment_date,
            projected_balance=projected_balance,
            reasoning=reasoning
        )
    
    def _timing_score(self, purchase_date: datetime, payment_date: datetime,
                     projected_balance: float) -> float:
        """Score based on payment timing relative to paychecks."""
        paychecks = self._count_paychecks_between(purchase_date, payment_date)
        
        if paychecks >= 2:
            return 35.0
        elif paychecks == 1 and projected_balance > 3000:
            return 24.5
        elif paychecks == 1:
            return 17.5
        else:
            return 7.0
    
    def _liquidity_score(self, projected_balance: float, amount: float) -> float:
        """Score based on available liquidity on payment date."""
        balance_after = projected_balance - amount
        
        if balance_after > 3000:
            return 25.0
        elif balance_after > 1500:
            return 15.0
        else:
            return 5.0
    
    def _savings_impact_score(self, payment_date: datetime, amount: float) -> float:
        """Score based on impact on savings goal."""
        paycheck_period = self._get_paycheck_period(payment_date)
        projected_savings_room = self._calculate_savings_room(paycheck_period, amount)
        
        if projected_savings_room >= self.savings_goal.amount_per_paycheck:
            return 15.0
        elif projected_savings_room >= self.savings_goal.amount_per_paycheck * 0.5:
            return 10.5
        else:
            return 4.5
    
    def _utilization_score(self, card: any, amount: float) -> float:
        """Score based on credit utilization."""
        new_balance = card.current_balance + amount
        utilization = (new_balance / card.credit_limit) if card.credit_limit > 0 else 0
        
        if utilization < 0.10:
            return 15.0
        elif utilization < 0.30:
            return 10.5
        else:
            return 6.0
    
    def _distribution_score(self, card: any) -> float:
        """Score based on transaction distribution."""
        util = (card.current_balance / card.credit_limit * 100) if card.credit_limit > 0 else 0
        
        if util < 20:
            return 10.0
        elif util < 50:
            return 7.0
        else:
            return 4.0
    
    def _calculate_payment_date(self, card: any, purchase_date: datetime) -> datetime:
        """Calculate when a purchase would be paid."""
        from dateutil.relativedelta import relativedelta
        
        closing_date = self._next_closing_date(card, purchase_date)
        payment_month_date = closing_date + relativedelta(months=1)
        payment_year = payment_month_date.year
        payment_month = payment_month_date.month
        max_day = calendar.monthrange(payment_year, payment_month)[1]
        valid_day = min(card.payment_due_day, max_day)
        payment_date = datetime(payment_year, payment_month, valid_day)
        
        return payment_date
    
    def _next_closing_date(self, card: any, purchase_date: datetime) -> datetime:
        """Find next closing date for a card."""
        try:
            closing_this_month = datetime(
                purchase_date.year,
                purchase_date.month,
                card.closing_day
            )
        except ValueError:
            last_day = calendar.monthrange(purchase_date.year, purchase_date.month)[1]
            closing_this_month = datetime(
                purchase_date.year,
                purchase_date.month,
                min(card.closing_day, last_day)
            )
        
        if purchase_date.day <= card.closing_day:
            return closing_this_month
        else:
            if purchase_date.month == 12:
                next_year = purchase_date.year + 1
                next_month = 1
            else:
                next_year = purchase_date.year
                next_month = purchase_date.month + 1
            
            try:
                return datetime(next_year, next_month, card.closing_day)
            except ValueError:
                last_day = calendar.monthrange(next_year, next_month)[1]
                return datetime(next_year, next_month, min(card.closing_day, last_day))
    
    def _project_balance(self, target_date: datetime) -> float:
        """Project checking account balance on a future date."""
        balance = self.current_balance
        today = datetime.now()
        fixed_monthly = getattr(self, 'fixed_expenses_monthly', 0)
        days_between = (target_date - today).days
        fixed_daily = fixed_monthly / 30
        balance -= (fixed_daily * days_between)
        variable_daily = self.savings_goal.variable_expenses_monthly / 30
        balance -= (variable_daily * days_between)
        paychecks = self._count_paychecks_between(today, target_date)
        balance += (paychecks * self.income_schedule.amount)
        
        return balance
    
    def _count_paychecks_between(self, start: datetime, end: datetime) -> int:
        """Count how many paychecks fall between two dates."""
        count = 0
        current_date = start
        
        while current_date <= end:
            if current_date.day == self.income_schedule.first_paycheck_day or \
               current_date.day == self.income_schedule.second_paycheck_day:
                count += 1
            current_date += timedelta(days=1)
        
        return count
    
    def _get_paycheck_period(self, date: datetime) -> str:
        """Determine which paycheck period a date falls in."""
        if date.day <= self.income_schedule.first_paycheck_day:
            return 'first'
        else:
            return 'second'
    
    def _calculate_savings_room(self, period: str, additional_expense: float) -> float:
        """Calculate how much can be saved in a paycheck period after expenses."""
        income = self.income_schedule.amount
        fixed_monthly = getattr(self, 'fixed_expenses_monthly', 0)
        fixed_period = fixed_monthly / 2
        variable_period = self.savings_goal.variable_expenses_monthly / 2
        available = income - fixed_period - variable_period - additional_expense
        
        return max(0, available)
    
    def _generate_reasoning(self, card: any, amount: float, payment_date: datetime,
                           projected_balance: float, timing_score: float,
                           liquidity_score: float, savings_score: float) -> str:
        """Generate human-readable reasoning."""
        reasons = []
        days_until = (payment_date - datetime.now()).days
        
        if timing_score >= 30:
            reasons.append(f"Timing excelente ({days_until} días)")
        elif timing_score >= 20:
            reasons.append(f"Timing bueno ({days_until} días)")
        
        if liquidity_score >= 20:
            reasons.append(f"Tendrás ${projected_balance:,.0f} disponible")
        elif liquidity_score >= 10:
            reasons.append(f"Balance ajustado (${projected_balance:,.0f})")
        else:
            reasons.append(f"⚠️ Balance bajo (${projected_balance:,.0f})")
        
        util = (card.current_balance / card.credit_limit * 100) if card.credit_limit > 0 else 0
        if util < 5:
            reasons.append("Tarjeta casi vacía")
        
        if savings_score >= 12:
            reasons.append("No afecta meta de ahorro")
        elif savings_score < 7:
            reasons.append("⚠️ Puede afectar ahorro")
        
        return " | ".join(reasons) if reasons else "Opción viable"
    
    def _check_liquidity(self, purchase_amount: float, purchase_date: datetime,
                        is_deferred: bool, payment_per_installment: float,
                        num_payments: int, payment_frequency: str) -> dict:
        """
        Check if user can afford purchase now or needs to wait.
        
        THREE LEVELS:
        - SAFE (Verde): Disponible > $1,500 después de compra
        - TIGHT (Amarillo): $500 < Disponible < $1,500
        - CRITICAL (Rojo): Disponible < $500 → ESPERAR
        
        Considers:
        - Current checking balance
        - Upcoming rent payment (day 1, funded by paycheck on day 15)
        - ALL credit card payments due this month (closed statements)
        - Required buffer ($1,000 minimum)
        - Savings goal ($500/month)
        - Upcoming paychecks
        """
        BUFFER_REQUIRED = 1000.0
        COMFORTABLE_BUFFER = 1500.0  # Verde: Más de esto disponible
        CRITICAL_THRESHOLD = 500.0   # Rojo: Menos de esto = ESPERAR
        RENT_DAY = 1
        RENT_PAYCHECK_DAY = 15
        
        current_checking = self.current_balance
        rent_amount = getattr(self, 'rent_amount', 3100.0)
        first_payment_amount = payment_per_installment if is_deferred else purchase_amount
        
        # Use purchase_date as reference, not today
        purchase_date_only = purchase_date.date() if isinstance(purchase_date, datetime) else purchase_date
        purchase_day = purchase_date_only.day
        today = datetime.now().date()
        
        # Project balance to purchase date
        projected_balance = self._project_balance(purchase_date)
        
        # Get all card payments due within 30 days from purchase date
        card_payments_this_month = getattr(self, 'card_payments_this_month', [])
        total_card_payments = sum(payment['amount'] for payment in card_payments_this_month)
        
        # Check if rent is upcoming from purchase date perspective
        rent_upcoming = False
        if purchase_day < RENT_DAY:
            rent_upcoming = True
        
        # Find next paycheck after purchase date
        next_paycheck_date = None
        if purchase_day < RENT_PAYCHECK_DAY:
            next_paycheck_date = datetime(purchase_date_only.year, purchase_date_only.month, RENT_PAYCHECK_DAY).date()
        else:
            from dateutil.relativedelta import relativedelta
            next_month = purchase_date_only + relativedelta(months=1)
            next_paycheck_date = datetime(next_month.year, next_month.month, RENT_PAYCHECK_DAY).date()
        
        # Calculate available after obligations
        available = projected_balance
        
        # Subtract upcoming obligations from purchase date perspective
        if rent_upcoming:
            available -= rent_amount
        
        # Subtract card payments due within 30 days
        available -= total_card_payments
        
        # Subtract OTHER unpaid fixed expenses (excluding rent which we counted above)
        fixed_expenses_pending = getattr(self, 'fixed_expenses_monthly', 0)
        if rent_upcoming:
            # Don't double-count rent
            fixed_expenses_pending -= rent_amount
        available -= fixed_expenses_pending
        
        # Subtract required buffer and savings
        available -= BUFFER_REQUIRED
        available -= self.savings_goal.amount_per_paycheck
        
        # Calculate remaining after purchase
        remaining_after_purchase = available - first_payment_amount
        
        # Determine liquidity status (3 levels)
        if remaining_after_purchase >= COMFORTABLE_BUFFER:
            liquidity_status = 'safe'
            can_afford = True
            status_emoji = '✅'
            status_text = 'Ahora'
            status_color = 'green'
        elif remaining_after_purchase >= CRITICAL_THRESHOLD:
            liquidity_status = 'tight'
            can_afford = True
            status_emoji = '⚠️'
            status_text = 'Ahora (Balance Ajustado)'
            status_color = 'yellow'
        else:
            liquidity_status = 'critical'
            can_afford = False
            status_emoji = '❌'
            status_text = 'Esperar'
            status_color = 'red'
        
        result = {
            'can_afford': can_afford,
            'liquidity_status': liquidity_status,
            'status_emoji': status_emoji,
            'status_text': status_text,
            'status_color': status_color,
            'current_checking': round(current_checking, 2),
            'projected_balance': round(projected_balance, 2),
            'available_after_obligations': round(available, 2),
            'remaining_after_purchase': round(remaining_after_purchase, 2),
            'required_amount': round(first_payment_amount, 2),
            'buffer_required': BUFFER_REQUIRED,
            'comfortable_buffer': COMFORTABLE_BUFFER,
            'critical_threshold': CRITICAL_THRESHOLD,
            'savings_goal': self.savings_goal.amount_per_paycheck,
            'rent_amount': round(rent_amount, 2) if rent_upcoming else 0,
            'card_payments_this_month': round(total_card_payments, 2),
            'card_payments_detail': card_payments_this_month,
            'next_paycheck_date': next_paycheck_date.isoformat() if next_paycheck_date else None
        }
        
        # Warning messages based on status
        if liquidity_status == 'critical':
            result['suggested_date'] = next_paycheck_date.isoformat() if next_paycheck_date else None
            result['reason'] = f"Balance muy bajo. Espera hasta {next_paycheck_date.strftime('%d %b')} (próximo paycheck) para tener liquidez suficiente"
            result['warning'] = f"⚠️ CRÍTICO: Quedarían solo ${remaining_after_purchase:,.2f} disponibles. Mínimo recomendado: ${CRITICAL_THRESHOLD:,.2f}"
        elif liquidity_status == 'tight':
            result['suggested_date'] = next_paycheck_date.isoformat() if next_paycheck_date else None
            result['warning'] = f"⚠️ ADVERTENCIA: Balance Muy Ajustado. Quedarán ${remaining_after_purchase:,.2f} disponibles después de la compra. Mínimo recomendado: ${COMFORTABLE_BUFFER:,.2f}. Considera esperar hasta {next_paycheck_date.strftime('%d %b')} para mayor seguridad."
        else:
            result['warning'] = None
            result['suggested_date'] = None
        
        return result
    
    def _count_payments_before_date(self, start_date: datetime, end_date: datetime,
                                    frequency: str) -> int:
        """Count how many payments occur between start and end date."""
        if not frequency:
            return 1
        
        days_diff = (end_date - start_date).days
        
        if frequency == 'weekly':
            return max(1, days_diff // 7)
        elif frequency == 'biweekly':
            return max(1, days_diff // 14)
        elif frequency == 'monthly':
            return max(1, days_diff // 30)
        
        return 1
    
    def _build_payment_schedule(self, card: any, purchase_date: datetime,
                                payment_amount: float, num_payments: int,
                                frequency: str) -> dict:
        """Build complete payment schedule."""
        schedule = []
        
        if frequency == 'weekly':
            interval_days = 7
        elif frequency == 'biweekly':
            interval_days = 14
        else:
            interval_days = 30
        
        for payment_num in range(1, num_payments + 1):
            expected_date = purchase_date + timedelta(days=interval_days * (payment_num - 1))
            statement_close = self._next_closing_date(card, expected_date)
            
            schedule.append({
                'payment_number': payment_num,
                'payment_amount': round(payment_amount, 2),
                'expected_date': expected_date.strftime('%Y-%m-%d'),
                'statement_close_date': statement_close.strftime('%Y-%m-%d'),
                'days_until': (expected_date - datetime.now()).days
            })
        
        return {
            'total_payments': num_payments,
            'payment_amount': round(payment_amount, 2),
            'frequency': frequency,
            'schedule': schedule
        }
