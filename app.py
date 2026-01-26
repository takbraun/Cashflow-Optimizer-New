"""
Cash Flow Optimizer + Savings Tracker
Main Flask application
"""

from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional
from functools import wraps
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# SQLite configuration for concurrent connections
# check_same_thread=False allows multiple Gunicorn workers to use the DB
# timeout=30 prevents "database is locked" errors under load
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cashflow.db?check_same_thread=False&timeout=30'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)

# SQLAlchemy pool configuration for concurrency
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,  # Verify connections before use
    'pool_recycle': 300,    # Recycle connections every 5 minutes
}

db = SQLAlchemy(app)


def enable_wal_mode():
    """Enable WAL mode for better concurrent read/write performance"""
    with app.app_context():
        db.session.execute(db.text('PRAGMA journal_mode=WAL'))
        db.session.execute(db.text('PRAGMA synchronous=NORMAL'))
        db.session.execute(db.text('PRAGMA busy_timeout=30000'))
        db.session.commit()

# ============================================================================
# MODELS
# ============================================================================

class Card(db.Model):
    """Credit card model"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    closing_day = db.Column(db.Integer, nullable=False)  # Day of month (1-31)
    payment_due_day = db.Column(db.Integer, nullable=False)  # Day of month for payment
    credit_limit = db.Column(db.Float, nullable=False)
    current_balance = db.Column(db.Float, default=0.0)  # Legacy field - will be deprecated
    balance_is_closed = db.Column(db.Boolean, default=False)  # Legacy field - will be deprecated
    closed_balance = db.Column(db.Float, default=0.0)  # Balance from closed statement (to pay this month)
    open_balance = db.Column(db.Float, default=0.0)  # Balance accumulating in current cycle
    manual_payment_date = db.Column(db.Date, nullable=True)  # Manual override for payment date
    apr = db.Column(db.Float, default=0.0)  # Annual Percentage Rate
    
    def __repr__(self):
        return f'<Card {self.name}>'
    
    def to_dict(self):
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        import calendar
        
        today = datetime.now().date()
        
        # Calculate billing cycles
        current_month = today.month
        current_year = today.year
        
        # Determine current billing cycle close date
        if today.day > self.closing_day:
            # We're AFTER closing day - in the NEW cycle
            # Previous cycle closed this month, current cycle closes next month
            previous_cycle_close = datetime(current_year, current_month, self.closing_day).date()
            current_cycle_close = (datetime(current_year, current_month, self.closing_day) + relativedelta(months=1)).date()
        else:
            # We're BEFORE closing day - still in previous cycle
            # Previous cycle closed last month, current cycle closes this month
            previous_cycle_close = (datetime(current_year, current_month, self.closing_day) - relativedelta(months=1)).date()
            current_cycle_close = datetime(current_year, current_month, self.closing_day).date()
        
        # Calculate payment dates - handle invalid days (like Feb 30)
        # Payment is on payment_due_day of the month AFTER closing
        def get_valid_payment_date(cycle_close_date):
            payment_month_date = cycle_close_date + relativedelta(months=1)
            payment_year = payment_month_date.year
            payment_month = payment_month_date.month
            
            # Get the last valid day of the payment month
            max_day = calendar.monthrange(payment_year, payment_month)[1]
            
            # Use the payment_due_day, but cap it at the max valid day
            valid_day = min(self.payment_due_day, max_day)
            
            return datetime(payment_year, payment_month, valid_day).date()
        
        # Calculate automatic payment dates
        previous_payment_date_auto = get_valid_payment_date(previous_cycle_close)
        current_payment_date_auto = get_valid_payment_date(current_cycle_close)
        
        # Use manual payment date if set and balance is closed, otherwise use calculated
        if self.manual_payment_date and self.balance_is_closed:
            previous_payment_date = self.manual_payment_date
        else:
            previous_payment_date = previous_payment_date_auto
        
        current_payment_date = current_payment_date_auto
        
        # Calculate days remaining
        days_until_previous_payment = (previous_payment_date - today).days
        days_until_current_close = (current_cycle_close - today).days
        days_until_current_payment = (current_payment_date - today).days
        
        # Get expenses for CLOSED statement (before previous_cycle_close)
        closed_expenses = VariableExpenseLog.query.filter(
            VariableExpenseLog.card_id == self.id,
            VariableExpenseLog.expense_date <= previous_cycle_close
        ).all()
        closed_expenses_total = sum(e.amount for e in closed_expenses)
        
        # Get payments made
        payments = CardPayment.query.filter(
            CardPayment.card_id == self.id
        ).all()
        total_paid = sum(p.amount for p in payments)
        
        # Calculate closed balance from expenses
        closed_balance_from_expenses = closed_expenses_total - total_paid
        closed_balance_from_expenses = max(0, closed_balance_from_expenses)
        
        # Get expenses for OPEN statement (after previous_cycle_close, before current_cycle_close)
        open_expenses = VariableExpenseLog.query.filter(
            VariableExpenseLog.card_id == self.id,
            VariableExpenseLog.expense_date > previous_cycle_close,
            VariableExpenseLog.expense_date <= current_cycle_close
        ).all()
        open_balance_from_expenses = sum(e.amount for e in open_expenses)
        
        # Use new fields if set, otherwise fall back to calculated or legacy values
        if self.closed_balance > 0 or self.open_balance > 0:
            # New system: use separate fields directly
            closed_balance = self.closed_balance
            open_balance = self.open_balance
        elif closed_expenses_total == 0 and open_balance_from_expenses == 0 and self.current_balance > 0:
            # Legacy system: use current_balance with balance_is_closed flag
            if self.balance_is_closed:
                closed_balance = self.current_balance
                open_balance = 0
            else:
                closed_balance = 0
                open_balance = self.current_balance
        else:
            # Use calculated values from expenses
            closed_balance = closed_balance_from_expenses
            open_balance = open_balance_from_expenses
        
        # Total balance
        total_balance = closed_balance + open_balance
        
        return {
            'id': self.id,
            'name': self.name,
            'closing_day': self.closing_day,
            'payment_due_day': self.payment_due_day,
            'credit_limit': self.credit_limit,
            'current_balance': round(total_balance, 2),  # Exactly 2 decimals
            'utilization': round((total_balance / self.credit_limit * 100), 2) if self.credit_limit > 0 else 0,
            'apr': self.apr,
            'manual_payment_date': self.manual_payment_date.isoformat() if self.manual_payment_date else None,
            
            # Closed statement (previous billing cycle)
            'closed_statement': {
                'balance': round(closed_balance, 2),  # Exactly 2 decimals
                'close_date': previous_cycle_close.isoformat(),
                'payment_date': previous_payment_date.isoformat(),
                'days_until_payment': days_until_previous_payment,
                'status': 'PAID' if closed_balance == 0 else 'PENDING',
                'has_manual_date': bool(self.manual_payment_date and self.balance_is_closed)
            },
            
            # Open statement (current billing cycle)
            'open_statement': {
                'balance': round(open_balance, 2),  # Exactly 2 decimals
                'close_date': current_cycle_close.isoformat(),
                'days_until_close': days_until_current_close,
                'payment_date': current_payment_date.isoformat(),
                'days_until_payment': days_until_current_payment
            }
        }


class Transaction(db.Model):
    """Transaction model"""
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey('card.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    purchase_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    payment_date = db.Column(db.DateTime, nullable=False)
    category = db.Column(db.String(50))
    
    def __repr__(self):
        return f'<Transaction {self.description} ${self.amount}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'card_id': self.card_id,
            'card_name': self.card.name if self.card else None,
            'amount': self.amount,
            'description': self.description,
            'purchase_date': self.purchase_date.isoformat(),
            'payment_date': self.payment_date.isoformat(),
            'category': self.category
        }


class Account(db.Model):
    """Checking account model"""
    id = db.Column(db.Integer, primary_key=True)
    balance = db.Column(db.Float, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Account balance=${self.balance}>'


class SavingsAccount(db.Model):
    """Emergency fund / savings account model"""
    id = db.Column(db.Integer, primary_key=True)
    balance = db.Column(db.Float, nullable=False)
    target = db.Column(db.Float, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Savings ${self.balance}/${self.target}>'
    
    def to_dict(self):
        return {
            'balance': self.balance,
            'target': self.target,
            'progress_pct': (self.balance / self.target * 100) if self.target > 0 else 0,
            'remaining': self.target - self.balance,
            'last_updated': self.last_updated.isoformat()
        }


class IncomeSchedule(db.Model):
    """Income schedule model"""
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    first_paycheck_day = db.Column(db.Integer, nullable=False)  # Day of month
    second_paycheck_day = db.Column(db.Integer, nullable=False)  # Day of month
    
    def __repr__(self):
        return f'<Income ${self.amount} on days {self.first_paycheck_day} and {self.second_paycheck_day}>'
    
    def to_dict(self):
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        import calendar
        
        today = datetime.now().date()
        current_day = today.day
        current_month = today.month
        current_year = today.year
        
        # Find next paycheck date
        paycheck_days = sorted([self.first_paycheck_day, self.second_paycheck_day])
        next_paycheck_date = None
        next_paycheck_amount = self.amount
        
        # Check both paycheck days this month
        for day in paycheck_days:
            try:
                paycheck_date = datetime(current_year, current_month, day).date()
                if paycheck_date >= today:
                    next_paycheck_date = paycheck_date
                    break
            except ValueError:
                # Invalid day for this month (e.g., Feb 30)
                continue
        
        # If no paycheck found this month, check next month
        if not next_paycheck_date:
            next_month = today + relativedelta(months=1)
            for day in paycheck_days:
                try:
                    paycheck_date = datetime(next_month.year, next_month.month, day).date()
                    next_paycheck_date = paycheck_date
                    break
                except ValueError:
                    continue
        
        # Format date in Spanish
        months_es = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                     'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        
        next_paycheck_formatted = None
        days_until = None
        if next_paycheck_date:
            next_paycheck_formatted = f"{next_paycheck_date.day} de {months_es[next_paycheck_date.month]}"
            days_until = (next_paycheck_date - today).days
        
        return {
            'amount': self.amount,
            'first_paycheck_day': self.first_paycheck_day,
            'second_paycheck_day': self.second_paycheck_day,
            'next_paycheck_date': next_paycheck_date.isoformat() if next_paycheck_date else None,
            'next_paycheck_formatted': next_paycheck_formatted,
            'days_until_paycheck': days_until
        }


class FixedExpense(db.Model):
    """Fixed monthly expenses"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    due_day = db.Column(db.Integer, nullable=False)  # Day of month
    category = db.Column(db.String(50))
    active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<FixedExpense {self.name} ${self.amount}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'amount': self.amount,
            'due_day': self.due_day,
            'category': self.category,
            'active': self.active
        }


class SavingsGoal(db.Model):
    """Savings goals and tracking"""
    id = db.Column(db.Integer, primary_key=True)
    amount_per_paycheck = db.Column(db.Float, nullable=False)
    min_balance_comfort = db.Column(db.Float, nullable=False)
    variable_expenses_monthly = db.Column(db.Float, nullable=False)
    
    def __repr__(self):
        return f'<SavingsGoal ${self.amount_per_paycheck}/paycheck>'
    
    def to_dict(self):
        return {
            'amount_per_paycheck': self.amount_per_paycheck,
            'min_balance_comfort': self.min_balance_comfort,
            'variable_expenses_monthly': self.variable_expenses_monthly
        }


class BonusEvent(db.Model):
    """One-time bonus or income events"""
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    expected_date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.String(200))
    received = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Bonus ${self.amount} on {self.expected_date}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'expected_date': self.expected_date.isoformat(),
            'description': self.description,
            'received': self.received
        }


class PurchaseRecommendation(db.Model):
    """Saved purchase recommendations with deferred payment options"""
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)  # Total amount
    purchase_date = db.Column(db.Date, nullable=False)
    is_deferred = db.Column(db.Boolean, default=False)
    num_payments = db.Column(db.Integer, nullable=True)  # Number of installments
    payment_frequency = db.Column(db.String(20), nullable=True)  # weekly/biweekly/monthly
    payment_amount = db.Column(db.Float, nullable=True)  # Amount per payment
    recommended_card_id = db.Column(db.Integer, db.ForeignKey('card.id'), nullable=False)
    can_afford_now = db.Column(db.Boolean, default=True)  # Has liquidity now
    liquidity_status = db.Column(db.String(20), default='safe')  # safe/tight/critical
    suggested_wait_date = db.Column(db.Date, nullable=True)  # If should wait
    status = db.Column(db.String(20), default='pending')  # pending/executed/cancelled
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    executed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship
    card = db.relationship('Card', backref='recommendations')
    
    def __repr__(self):
        return f'<PurchaseRecommendation ${self.amount} on {self.card.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'amount': round(self.amount, 2),
            'purchase_date': self.purchase_date.isoformat(),
            'is_deferred': self.is_deferred,
            'num_payments': self.num_payments,
            'payment_frequency': self.payment_frequency,
            'payment_amount': round(self.payment_amount, 2) if self.payment_amount else None,
            'recommended_card_id': self.recommended_card_id,
            'recommended_card_name': self.card.name,
            'can_afford_now': self.can_afford_now,
            'liquidity_status': self.liquidity_status,
            'suggested_wait_date': self.suggested_wait_date.isoformat() if self.suggested_wait_date else None,
            'status': self.status,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'executed_at': self.executed_at.isoformat() if self.executed_at else None
        }


class DeferredPaymentSchedule(db.Model):
    """Schedule of deferred payments for tracking"""
    id = db.Column(db.Integer, primary_key=True)
    recommendation_id = db.Column(db.Integer, db.ForeignKey('purchase_recommendation.id'), nullable=False)
    payment_number = db.Column(db.Integer, nullable=False)  # 1, 2, 3...
    payment_amount = db.Column(db.Float, nullable=False)
    expected_date = db.Column(db.Date, nullable=False)
    card_statement_close_date = db.Column(db.Date, nullable=False)  # Which statement this falls into
    status = db.Column(db.String(20), default='pending')  # pending/paid
    
    # Relationship
    recommendation = db.relationship('PurchaseRecommendation', backref='payment_schedule')
    
    def __repr__(self):
        return f'<DeferredPayment #{self.payment_number} ${self.payment_amount}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'recommendation_id': self.recommendation_id,
            'payment_number': self.payment_number,
            'payment_amount': round(self.payment_amount, 2),
            'expected_date': self.expected_date.isoformat(),
            'card_statement_close_date': self.card_statement_close_date.isoformat(),
            'status': self.status
        }


class ExpensePayment(db.Model):
    """Track when fixed expenses are actually paid"""
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('fixed_expense.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # Month this payment is for
    year = db.Column(db.Integer, nullable=False)   # Year this payment is for
    notes = db.Column(db.String(200))
    
    expense = db.relationship('FixedExpense', backref='payments')
    
    def __repr__(self):
        return f'<ExpensePayment {self.expense.name if self.expense else "Unknown"} ${self.amount}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'expense_id': self.expense_id,
            'expense_name': self.expense.name if self.expense else None,
            'amount': self.amount,
            'payment_date': self.payment_date.isoformat(),
            'month': self.month,
            'year': self.year,
            'notes': self.notes
        }


class ExpenseCategory(db.Model):
    """Custom categories for variable expenses"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    icon = db.Column(db.String(10), default='📌')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ExpenseCategory {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon
        }


class VariableExpenseLog(db.Model):
    """Log of variable expenses (comida, gasolina, etc)"""
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    expense_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    card_id = db.Column(db.Integer, db.ForeignKey('card.id'), nullable=True)  # Puede ser efectivo
    
    card = db.relationship('Card', backref='variable_expenses')
    
    def __repr__(self):
        return f'<VariableExpense {self.category} ${self.amount}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'amount': self.amount,
            'description': self.description,
            'expense_date': self.expense_date.isoformat(),
            'card_id': self.card_id,
            'card_name': self.card.name if self.card else 'Efectivo'
        }


class CardPayment(db.Model):
    """Track credit card payments from checking account"""
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey('card.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.String(200))
    
    card = db.relationship('Card', backref='payments')
    
    def __repr__(self):
        return f'<CardPayment {self.card.name if self.card else "Unknown"} ${self.amount}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'card_id': self.card_id,
            'card_name': self.card.name if self.card else None,
            'amount': self.amount,
            'payment_date': self.payment_date.isoformat(),
            'notes': self.notes
        }


class CardAlias(db.Model):
    """Map Apple Pay card names to app card IDs"""
    id = db.Column(db.Integer, primary_key=True)
    apple_name = db.Column(db.String(100), nullable=False, unique=True)  # Name from Apple Pay
    card_id = db.Column(db.Integer, db.ForeignKey('card.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    card = db.relationship('Card', backref='aliases')

    def __repr__(self):
        return f'<CardAlias "{self.apple_name}" -> {self.card.name if self.card else "Unknown"}>'

    def to_dict(self):
        return {
            'id': self.id,
            'apple_name': self.apple_name,
            'card_id': self.card_id,
            'card_name': self.card.name if self.card else None,
            'created_at': self.created_at.isoformat()
        }


class PendingApplePayExpense(db.Model):
    """Store Apple Pay expenses that couldn't be matched to a card"""
    id = db.Column(db.Integer, primary_key=True)
    apple_card_name = db.Column(db.String(100), nullable=False)  # Original name from Apple Pay
    amount = db.Column(db.Float, nullable=False)
    merchant = db.Column(db.String(200))
    user = db.Column(db.String(50))
    transaction_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, resolved, ignored
    resolved_card_id = db.Column(db.Integer, db.ForeignKey('card.id'), nullable=True)
    resolved_expense_id = db.Column(db.Integer, nullable=True)  # Link to created expense
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

    resolved_card = db.relationship('Card', backref='resolved_pending_expenses')

    def __repr__(self):
        return f'<PendingApplePayExpense "{self.apple_card_name}" ${self.amount} ({self.status})>'

    def to_dict(self):
        return {
            'id': self.id,
            'apple_card_name': self.apple_card_name,
            'amount': self.amount,
            'merchant': self.merchant,
            'user': self.user,
            'transaction_date': self.transaction_date.isoformat(),
            'status': self.status,
            'resolved_card_id': self.resolved_card_id,
            'resolved_card_name': self.resolved_card.name if self.resolved_card else None,
            'resolved_expense_id': self.resolved_expense_id,
            'created_at': self.created_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


# ============================================================================
# APPLE PAY INTEGRATION HELPERS
# ============================================================================

# Merchant to category mapping for auto-categorization
MERCHANT_CATEGORIES = {
    # Comida/Restaurantes
    'starbucks': 'Comida/Restaurantes',
    'mcdonald': 'Comida/Restaurantes',
    'chipotle': 'Comida/Restaurantes',
    'uber eats': 'Comida/Restaurantes',
    'doordash': 'Comida/Restaurantes',
    'restaurant': 'Comida/Restaurantes',
    'cafe': 'Comida/Restaurantes',
    'pizza': 'Comida/Restaurantes',
    'taco': 'Comida/Restaurantes',
    'burger': 'Comida/Restaurantes',
    'sushi': 'Comida/Restaurantes',
    'wendy': 'Comida/Restaurantes',
    'chick-fil-a': 'Comida/Restaurantes',
    'popeyes': 'Comida/Restaurantes',
    'panera': 'Comida/Restaurantes',
    'subway': 'Comida/Restaurantes',
    'dunkin': 'Comida/Restaurantes',

    # Groceries
    'walmart': 'Groceries',
    'target': 'Groceries',
    'costco': 'Groceries',
    'whole foods': 'Groceries',
    'trader joe': 'Groceries',
    'kroger': 'Groceries',
    'safeway': 'Groceries',
    'grocery': 'Groceries',
    'heb': 'Groceries',
    'aldi': 'Groceries',
    'publix': 'Groceries',

    # Gasolina
    'shell': 'Gasolina',
    'chevron': 'Gasolina',
    'exxon': 'Gasolina',
    'mobil': 'Gasolina',
    'bp ': 'Gasolina',
    'gas station': 'Gasolina',
    'fuel': 'Gasolina',
    'circle k': 'Gasolina',
    '7-eleven': 'Gasolina',

    # Transporte
    'uber': 'Transporte',
    'lyft': 'Transporte',
    'parking': 'Transporte',

    # Entretenimiento
    'netflix': 'Entretenimiento',
    'spotify': 'Entretenimiento',
    'hulu': 'Entretenimiento',
    'disney': 'Entretenimiento',
    'movie': 'Entretenimiento',
    'cinema': 'Entretenimiento',
    'amc': 'Entretenimiento',

    # Shopping
    'amazon': 'Shopping personal',
    'apple store': 'Shopping personal',
    'best buy': 'Shopping personal',
    'mall': 'Shopping personal',

    # Salud
    'pharmacy': 'Salud',
    'cvs': 'Salud',
    'walgreens': 'Salud',
}

# Card name aliases for matching
CARD_ALIASES = {
    'bank of america': 'bofa',
    'american express': 'amex',
    'citibank': 'citi',
    'apple': 'apple card',
}


def match_card_by_name(card_name_from_shortcut, create_alias_if_fuzzy=True):
    """
    Match card name from iOS Shortcuts to database card.

    Priority:
    1. Check CardAlias table (user-defined mappings)
    2. Check hardcoded CARD_ALIASES
    3. Exact match on Card.name
    4. Fuzzy/substring match

    Returns: (card, match_type) tuple
    - match_type: 'alias_db', 'alias_hardcoded', 'exact', 'fuzzy', None
    """
    if not card_name_from_shortcut:
        return None, None

    original_name = card_name_from_shortcut.strip()
    card_name = original_name.lower()

    # 1. Check CardAlias table first (user-defined mappings)
    alias = CardAlias.query.filter(
        db.func.lower(CardAlias.apple_name) == card_name
    ).first()
    if alias:
        return alias.card, 'alias_db'

    # 2. Check hardcoded aliases
    for alias_key, canonical in CARD_ALIASES.items():
        if alias_key in card_name:
            card = Card.query.filter(
                db.func.lower(Card.name) == canonical
            ).first()
            if card:
                return card, 'alias_hardcoded'

    # 3. Try exact match
    card = Card.query.filter(
        db.func.lower(Card.name) == card_name
    ).first()
    if card:
        return card, 'exact'

    # 4. Try fuzzy/substring match
    cards = Card.query.all()
    for card in cards:
        if card_name in card.name.lower() or card.name.lower() in card_name:
            # Auto-create alias for future matches
            if create_alias_if_fuzzy:
                try:
                    new_alias = CardAlias(
                        apple_name=original_name,
                        card_id=card.id
                    )
                    db.session.add(new_alias)
                    db.session.commit()
                    print(f"[ALIAS] Auto-created: '{original_name}' -> {card.name}")
                except Exception as e:
                    print(f"[ALIAS] Could not auto-create alias: {e}")
                    db.session.rollback()
            return card, 'fuzzy'

    return None, None


def categorize_by_merchant(merchant_name):
    """
    Auto-categorize expense based on merchant name.
    Returns (category, source) tuple.
    """
    if not merchant_name:
        return ('Otros', 'default')

    merchant_lower = merchant_name.lower()

    for keyword, category in MERCHANT_CATEGORIES.items():
        if keyword in merchant_lower:
            return (category, 'merchant_match')

    return ('Otros', 'default')


def require_apple_pay_api_key(f):
    """Decorator to require Apple Pay API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = request.json or {}
        api_key = data.get('api_key') or request.headers.get('X-API-Key')
        expected_key = os.getenv('APPLE_PAY_API_KEY')

        if not expected_key:
            return jsonify({'error': 'Apple Pay integration not configured'}), 503

        if not api_key or api_key != expected_key:
            return jsonify({'error': 'Invalid API key'}), 401

        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')


@app.route('/api/dashboard')
def dashboard_data():
    """Get all dashboard data"""
    
    # Get current balances
    account = Account.query.first()
    savings = SavingsAccount.query.first()
    
    # Get cards
    cards = Card.query.all()
    cards_data = [c.to_dict() for c in cards]
    
    # Calculate debt summary
    total_closed = sum(c['closed_statement']['balance'] for c in cards_data)
    total_open = sum(c['open_statement']['balance'] for c in cards_data)
    total_debt = total_closed + total_open
    
    # Cards grouped by statement type
    closed_cards = [
        {
            'name': c['name'],
            'balance': c['closed_statement']['balance'],
            'payment_date': c['closed_statement']['payment_date'],
            'days_until_payment': c['closed_statement']['days_until_payment']
        }
        for c in cards_data if c['closed_statement']['balance'] > 0
    ]
    
    open_cards = [
        {
            'name': c['name'],
            'balance': c['open_statement']['balance'],
            'payment_date': c['open_statement']['payment_date'],
            'days_until_payment': c['open_statement']['days_until_payment']
        }
        for c in cards_data if c['open_statement']['balance'] > 0
    ]
    
    # Get next paychecks
    income = IncomeSchedule.query.first()
    
    # Get savings goal
    savings_goal = SavingsGoal.query.first()
    
    # Get expense categories
    categories = ExpenseCategory.query.order_by(ExpenseCategory.name).all()
    
    return jsonify({
        'checking_balance': account.balance if account else 0,
        'savings': savings.to_dict() if savings else None,
        'cards': cards_data,
        'income': income.to_dict() if income else None,
        'savings_goal': savings_goal.to_dict() if savings_goal else None,
        'expense_categories': [c.to_dict() for c in categories],
        'debt_summary': {
            'total_closed': round(total_closed, 2),
            'total_open': round(total_open, 2),
            'total_debt': round(total_debt, 2),
            'closed_cards': closed_cards,
            'open_cards': open_cards
        }
    })


@app.route('/api/recommend', methods=['POST'])
def recommend_card():
    """
    Recommend best card for a purchase with deferred payment support
    
    POST body:
    {
        "amount": 500.00,
        "date": "2026-01-05",  # optional, defaults to today
        "is_deferred": false,
        "num_payments": 6,  # optional, if deferred
        "payment_frequency": "monthly",  # optional: weekly/biweekly/monthly
        "description": "iPhone 15",  # optional
        "save": true  # optional, whether to save recommendation
    }
    """
    try:
        data = request.json
        amount = float(data['amount'])
        purchase_date_str = data.get('date')
        is_deferred = data.get('is_deferred', False)
        num_payments = data.get('num_payments')
        payment_frequency = data.get('payment_frequency', 'monthly')
        description = data.get('description', '')
        should_save = data.get('save', True)
        
        if purchase_date_str:
            # Parse date string and force it to be treated as local date (no timezone conversion)
            if 'T' in purchase_date_str:
                # Has time component, parse as datetime
                purchase_date = datetime.fromisoformat(purchase_date_str.replace('Z', '+00:00'))
            else:
                # Just a date like "2026-01-10", parse as date and use midnight
                purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d')
        else:
            purchase_date = datetime.now()
        
        # Validate deferred payment params
        if is_deferred and not num_payments:
            return jsonify({'error': 'num_payments required when is_deferred is true'}), 400
        
        # Get all necessary data
        cards = Card.query.all()
        account = Account.query.first()
        income = IncomeSchedule.query.first()
        savings_goal = SavingsGoal.query.first()
        
        if not all([cards, account, income, savings_goal]):
            return jsonify({'error': 'Sistema no configurado. Configure tarjetas, cuenta e ingresos.'}), 400
        
        # Get fixed expenses for liquidity check - ONLY UNPAID THIS MONTH
        today = datetime.now()
        fixed_expenses = FixedExpense.query.filter_by(active=True).all()
        
        # Calculate which expenses are NOT yet paid this month
        unpaid_fixed_expenses = []
        for expense in fixed_expenses:
            # Check if already paid this month
            payment = ExpensePayment.query.filter_by(
                expense_id=expense.id,
                month=today.month,
                year=today.year
            ).first()
            
            if not payment:
                # Not paid yet - include in pending
                unpaid_fixed_expenses.append(expense)
        
        fixed_expenses_monthly = sum(e.amount for e in unpaid_fixed_expenses)
        rent_amount = max([e.amount for e in unpaid_fixed_expenses], default=0)  # Largest unpaid expense
        
        # Calculate card payments due within 30 days FROM PURCHASE DATE
        from datetime import datetime as dt
        purchase_date_for_calc = purchase_date.date() if isinstance(purchase_date, datetime) else purchase_date
        
        card_payments_this_month = []
        for card in cards:
            card_dict = card.to_dict()
            
            # Get closed statement payment info (corrected key name)
            closed_statement = card_dict.get('closed_statement', {})
            if closed_statement.get('balance', 0) > 0:
                payment_date_str = closed_statement.get('payment_date')
                if payment_date_str:
                    card_payment_date = dt.fromisoformat(payment_date_str).date()
                    
                    # Check if payment is due within 30 days FROM PURCHASE DATE
                    days_until_payment = (card_payment_date - purchase_date_for_calc).days
                    
                    if 0 <= days_until_payment <= 30:
                        card_payments_this_month.append({
                            'card_name': card.name,
                            'amount': closed_statement['balance'],
                            'payment_date': payment_date_str,
                            'days_until': days_until_payment
                        })
        
        # Create recommendation engine
        from recommendation_engine import CardRecommendationEngine
        
        engine = CardRecommendationEngine(
            cards=cards,
            current_balance=account.balance,
            income_schedule=income,
            savings_goal=savings_goal
        )
        
        # Pass additional data needed for liquidity check
        engine.rent_amount = rent_amount
        engine.fixed_expenses_monthly = fixed_expenses_monthly
        engine.card_payments_this_month = card_payments_this_month  # ← NUEVO
        
        # Get recommendations with liquidity check
        result = engine.recommend(
            amount, 
            purchase_date,
            is_deferred,
            num_payments,
            payment_frequency
        )
        
        # Save recommendation if requested
        saved_recommendation = None
        if should_save and result['recommendations']:
            best_card = result['recommendations'][0].card
            
            recommendation = PurchaseRecommendation(
                amount=amount,
                purchase_date=purchase_date.date(),
                is_deferred=is_deferred,
                num_payments=num_payments if is_deferred else None,
                payment_frequency=payment_frequency if is_deferred else None,
                payment_amount=amount / num_payments if is_deferred and num_payments else amount,
                recommended_card_id=best_card.id,
                can_afford_now=result['can_afford_now'],
                liquidity_status=result['liquidity_analysis'].get('liquidity_status', 'safe'),
                suggested_wait_date=datetime.fromisoformat(result['suggested_wait_date']).date() if result.get('suggested_wait_date') and result['suggested_wait_date'] else None,
                status='pending',
                description=description
            )
            
            db.session.add(recommendation)
            db.session.commit()
            db.session.refresh(recommendation)
            
            # Save deferred payment schedule if applicable
            if is_deferred and result.get('deferred_schedule'):
                for payment_info in result['deferred_schedule']['schedule']:
                    schedule_entry = DeferredPaymentSchedule(
                        recommendation_id=recommendation.id,
                        payment_number=payment_info['payment_number'],
                        payment_amount=payment_info['payment_amount'],
                        expected_date=datetime.fromisoformat(payment_info['expected_date']).date(),
                        card_statement_close_date=datetime.fromisoformat(payment_info['statement_close_date']).date(),
                        status='pending'
                    )
                    db.session.add(schedule_entry)
                
                db.session.commit()
            
            saved_recommendation = recommendation.to_dict()
        
        return jsonify({
            'can_afford_now': result['can_afford_now'],
            'suggested_wait_date': result.get('suggested_wait_date'),
            'liquidity_analysis': result['liquidity_analysis'],
            'recommendations': [r.to_dict() for r in result['recommendations']],
            'deferred_schedule': result.get('deferred_schedule'),
            'saved_recommendation': saved_recommendation
        })
        
    except Exception as e:
        print(f"Error in recommend: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    """Get all pending purchase recommendations"""
    try:
        recommendations = PurchaseRecommendation.query.filter_by(status='pending').order_by(PurchaseRecommendation.created_at.desc()).all()
        
        result = []
        for rec in recommendations:
            rec_dict = rec.to_dict()
            
            # Include payment schedule if deferred
            if rec.is_deferred:
                schedule = DeferredPaymentSchedule.query.filter_by(recommendation_id=rec.id).order_by(DeferredPaymentSchedule.payment_number).all()
                rec_dict['payment_schedule'] = [s.to_dict() for s in schedule]
            
            result.append(rec_dict)
        
        return jsonify({'recommendations': result})
        
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/recommendations/<int:rec_id>/execute', methods=['POST'])
def execute_recommendation(rec_id):
    """Execute a saved recommendation - creates actual expense and updates card balance"""
    try:
        recommendation = PurchaseRecommendation.query.get(rec_id)
        
        if not recommendation:
            return jsonify({'error': 'Recomendación no encontrada'}), 404
        
        if recommendation.status == 'executed':
            return jsonify({'error': 'Esta recomendación ya fue ejecutada'}), 400
        
        # Create variable expense log with full amount
        expense = VariableExpenseLog(
            category=recommendation.description or 'Compra',
            amount=recommendation.amount,
            description=f"Ejecutado desde recomendación #{recommendation.id}" + (f" - {recommendation.description}" if recommendation.description else ""),
            expense_date=recommendation.purchase_date,
            card_id=recommendation.recommended_card_id
        )
        
        db.session.add(expense)
        
        # Update card balance (full amount goes to card immediately)
        card = Card.query.get(recommendation.recommended_card_id)
        card.current_balance += recommendation.amount
        
        # Mark recommendation as executed
        recommendation.status = 'executed'
        recommendation.executed_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Compra de ${recommendation.amount:.2f} ejecutada en {card.name}',
            'expense': expense.to_dict(),
            'updated_card': card.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error executing recommendation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/recommendations/<int:rec_id>/cancel', methods=['POST'])
def cancel_recommendation(rec_id):
    """Cancel a pending recommendation"""
    try:
        recommendation = PurchaseRecommendation.query.get(rec_id)
        
        if not recommendation:
            return jsonify({'error': 'Recomendación no encontrada'}), 404
        
        if recommendation.status == 'executed':
            return jsonify({'error': 'No se puede cancelar una recomendación ya ejecutada'}), 400
        
        recommendation.status = 'cancelled'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Recomendación cancelada'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error cancelling recommendation: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/recommendations/execute-batch', methods=['POST'])
def execute_batch_recommendations():
    """Execute multiple recommendations at once"""
    try:
        data = request.json
        recommendation_ids = data.get('ids', [])
        
        if not recommendation_ids:
            return jsonify({'error': 'No se proporcionaron IDs de recomendaciones'}), 400
        
        results = []
        errors = []
        
        for rec_id in recommendation_ids:
            recommendation = PurchaseRecommendation.query.get(rec_id)
            
            if not recommendation:
                errors.append(f'Recomendación #{rec_id} no encontrada')
                continue
            
            if recommendation.status == 'executed':
                errors.append(f'Recomendación #{rec_id} ya fue ejecutada')
                continue
            
            try:
                # Create variable expense log
                expense = VariableExpenseLog(
                    category=recommendation.description or 'Compra',
                    amount=recommendation.amount,
                    description=f"Ejecutado desde recomendación #{recommendation.id}" + (f" - {recommendation.description}" if recommendation.description else ""),
                    expense_date=recommendation.purchase_date,
                    card_id=recommendation.recommended_card_id
                )
                
                db.session.add(expense)
                
                # Update card balance
                card = Card.query.get(recommendation.recommended_card_id)
                card.current_balance += recommendation.amount
                
                # Mark as executed
                recommendation.status = 'executed'
                recommendation.executed_at = datetime.utcnow()
                
                results.append({
                    'id': rec_id,
                    'amount': recommendation.amount,
                    'card': card.name
                })
                
            except Exception as e:
                errors.append(f'Error ejecutando recomendación #{rec_id}: {str(e)}')
                continue
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'executed': len(results),
            'results': results,
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in batch execute: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/cards', methods=['GET', 'POST'])
def cards_api():
    """Get all cards or create new card"""
    if request.method == 'GET':
        cards = Card.query.all()
        return jsonify([c.to_dict() for c in cards])
    
    elif request.method == 'POST':
        data = request.json
        card = Card(
            name=data['name'],
            closing_day=int(data['closing_day']),
            payment_days_after=int(data['payment_days_after']),
            credit_limit=float(data['credit_limit']),
            current_balance=float(data.get('current_balance', 0)),
            color=data.get('color', '#0066cc')
        )
        db.session.add(card)
        db.session.commit()
        return jsonify(card.to_dict()), 201


@app.route('/api/savings/transfer', methods=['POST'])
def transfer_to_savings():
    """Transfer money to savings"""
    data = request.json
    amount = float(data['amount'])
    
    account = Account.query.first()
    savings = SavingsAccount.query.first()
    
    if account.balance < amount:
        return jsonify({'error': 'Insufficient funds'}), 400
    
    account.balance -= amount
    savings.balance += amount
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'new_checking_balance': account.balance,
        'new_savings_balance': savings.balance
    })


@app.route('/api/savings/calculate-available', methods=['GET'])
def calculate_available_for_savings():
    """Calculate how much can be transferred to savings"""
    from cash_flow_calculator import CashFlowCalculator
    
    account = Account.query.first()
    savings_goal = SavingsGoal.query.first()
    income = IncomeSchedule.query.first()
    
    calculator = CashFlowCalculator(
        current_balance=account.balance,
        income_schedule=income,
        savings_goal=savings_goal
    )
    
    available = calculator.calculate_available_for_savings()
    
    return jsonify(available)


@app.route('/api/balance/update', methods=['POST'])
def update_balance():
    """Manually update checking account balance"""
    data = request.json
    new_balance = float(data['balance'])
    
    account = Account.query.first()
    old_balance = account.balance
    account.balance = new_balance
    account.last_updated = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'old_balance': old_balance,
        'new_balance': new_balance,
        'last_updated': account.last_updated.isoformat()
    })


@app.route('/api/expenses/fixed/mark-paid', methods=['POST'])
def mark_expense_paid():
    """Mark a fixed expense as paid for current month"""
    data = request.json
    expense_id = int(data['expense_id'])
    
    # Allow custom payment date
    payment_date_str = data.get('payment_date')
    if payment_date_str:
        payment_date = datetime.fromisoformat(payment_date_str)
    else:
        payment_date = datetime.now()
    
    amount = float(data.get('amount'))  # Allow override of amount
    
    # NEW: Payment method and card info
    payment_method = data.get('payment_method', 'cash')  # 'cash' or 'card'
    card_id = data.get('card_id')
    already_in_balance = data.get('already_in_balance', False)
    
    expense = FixedExpense.query.get(expense_id)
    if not expense:
        return jsonify({'error': 'Expense not found'}), 404
    
    # Check if already paid for that specific month/year
    existing = ExpensePayment.query.filter_by(
        expense_id=expense_id,
        month=payment_date.month,
        year=payment_date.year
    ).first()
    
    if existing:
        return jsonify({'error': f'Already marked as paid for {payment_date.strftime("%B %Y")}'}), 400
    
    # Create payment record
    payment = ExpensePayment(
        expense_id=expense_id,
        amount=amount if amount else expense.amount,
        payment_date=payment_date,
        month=payment_date.month,
        year=payment_date.year,
        notes=data.get('notes', '')
    )
    
    response_data = {
        'success': True,
        'payment': payment.to_dict(),
        'checking_updated': False,
        'card_updated': False
    }
    
    # Handle payment based on method
    if payment_method == 'cash':
        # Deduct from checking account
        account = Account.query.first()
        old_checking = account.balance
        account.balance -= payment.amount
        account.last_updated = datetime.utcnow()
        
        response_data['checking_updated'] = True
        response_data['old_checking'] = old_checking
        response_data['new_checking'] = account.balance
        
    elif payment_method == 'card' and card_id:
        # Add to card balance (only if not already in balance)
        card = Card.query.get(int(card_id))
        if not card:
            return jsonify({'error': 'Card not found'}), 404
        
        old_card_balance = card.open_balance
        
        if not already_in_balance:
            # Add to open balance (current billing cycle)
            card.open_balance += payment.amount
            
            response_data['card_updated'] = True
            response_data['card_name'] = card.name
            response_data['old_card_balance'] = old_card_balance
            response_data['new_card_balance'] = card.open_balance
        else:
            # Just mark as paid, no balance changes
            response_data['card_updated'] = False
            response_data['note'] = 'Marked as paid without balance changes (already included)'
    
    db.session.add(payment)
    db.session.commit()
    
    return jsonify(response_data)


@app.route('/api/expenses/fixed/add', methods=['POST'])
def add_fixed_expense():
    """Add a new fixed expense"""
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('name') or not data.get('amount'):
            return jsonify({'error': 'Nombre y monto son requeridos'}), 400
        
        # Create new fixed expense
        expense = FixedExpense(
            name=data['name'],
            amount=float(data['amount']),
            due_day=int(data.get('due_day', 1)),
            category=data.get('category', ''),
            active=True
        )
        
        db.session.add(expense)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'expense': expense.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error adding fixed expense: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error al agregar gasto fijo: {str(e)}'}), 500


@app.route('/api/expenses/fixed/<int:expense_id>/edit', methods=['PUT'])
def edit_fixed_expense(expense_id):
    """Edit a fixed expense"""
    try:
        expense = FixedExpense.query.get(expense_id)
        if not expense:
            return jsonify({'error': 'Gasto fijo no encontrado'}), 404
        
        data = request.json
        
        # Update fields if provided
        if 'name' in data:
            expense.name = data['name']
        
        if 'amount' in data:
            expense.amount = float(data['amount'])
        
        if 'due_day' in data:
            expense.due_day = int(data['due_day'])
        
        if 'category' in data:
            expense.category = data['category']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'expense': expense.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error editing fixed expense: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error al editar gasto fijo: {str(e)}'}), 500


@app.route('/api/expenses/variable/add', methods=['POST'])
def add_variable_expense():
    """Add a variable expense (comida, gasolina, etc)"""
    data = request.json
    
    card_id = data.get('card_id')
    expense_date = datetime.fromisoformat(data.get('expense_date', datetime.now().isoformat()))
    
    expense = VariableExpenseLog(
        category=data['category'],
        amount=float(data['amount']),
        description=data.get('description', ''),
        expense_date=expense_date,
        card_id=int(card_id) if card_id and card_id != '' else None
    )
    
    account = Account.query.first()
    card_balance_updated = None
    
    # If paid with card, update card balance
    if expense.card_id:
        card = Card.query.get(expense.card_id)
        if card:
            # Determine if this expense goes to closed or open statement
            # Based on card's closing day and current date
            today = datetime.now().date()
            expense_day = expense_date.day
            current_day = today.day
            
            # CRITICAL LOGIC:
            # - CLOSED period = already passed closing day, waiting for payment
            # - OPEN period = current period, before next closing day
            
            # If we've already passed this month's closing day, we're in OPEN period
            # If we haven't reached closing day yet, we're still in OPEN period
            # CLOSED is only for charges from LAST billing cycle
            
            # Simple rule: All new charges go to OPEN (current billing cycle)
            # CLOSED is manually set when you close a statement
            card.open_balance += expense.amount
            statement_used = 'OPEN'
            
            card_balance_updated = {
                'card_name': card.name,
                'closed_balance': card.closed_balance,
                'open_balance': card.open_balance
            }
        # Don't deduct from checking - it will be paid later with card
    else:
        # If paid with cash/debit, deduct from checking
        account.balance -= expense.amount
    
    account.last_updated = datetime.utcnow()

    db.session.add(expense)
    db.session.commit()

    # Index expense in RAG system (non-blocking)
    try:
        engine = get_insights_engine()
        if engine:
            engine.index_expense(expense)
    except Exception as e:
        print(f"RAG indexing error (non-critical): {e}")

    return jsonify({
        'success': True,
        'expense': expense.to_dict(),
        'new_balance': account.balance,
        'card_updated': card_balance_updated
    })


@app.route('/api/expenses/variable/<int:expense_id>/edit', methods=['POST'])
def edit_variable_expense(expense_id):
    """Edit a variable expense and update balances accordingly"""
    data = request.json
    
    expense = VariableExpenseLog.query.get(expense_id)
    if not expense:
        return jsonify({'error': 'Expense not found'}), 404
    
    # Store old values for reversal
    old_amount = expense.amount
    old_card_id = expense.card_id
    old_expense_date = expense.expense_date
    
    # New values
    new_amount = float(data.get('amount', expense.amount))
    new_card_id = data.get('card_id')
    if new_card_id == '' or new_card_id == 'null':
        new_card_id = None
    else:
        new_card_id = int(new_card_id) if new_card_id else None
    
    new_expense_date = datetime.fromisoformat(data.get('expense_date', expense.expense_date.isoformat()))
    
    account = Account.query.first()
    
    # STEP 1: Reverse old transaction
    if old_card_id:
        # Was on card - remove from card balance
        # Need to determine which balance it was in originally
        old_card = Card.query.get(old_card_id)
        if old_card:
            # Try to remove from open first (most common)
            if old_card.open_balance >= old_amount:
                old_card.open_balance -= old_amount
            else:
                # Must be in closed
                old_card.closed_balance -= old_amount
    else:
        # Was cash - add back to checking
        account.balance += old_amount
    
    # STEP 2: Apply new transaction
    card_balance_updated = None
    if new_card_id:
        # Put on card - ALWAYS goes to OPEN (current billing cycle)
        new_card = Card.query.get(new_card_id)
        if new_card:
            new_card.open_balance += new_amount
            
            card_balance_updated = {
                'card_name': new_card.name,
                'closed_balance': new_card.closed_balance,
                'open_balance': new_card.open_balance
            }
    else:
        # Cash - deduct from checking
        account.balance -= new_amount
    
    # Update expense
    expense.category = data.get('category', expense.category)
    expense.amount = new_amount
    expense.description = data.get('description', expense.description)
    expense.expense_date = new_expense_date
    expense.card_id = new_card_id
    
    account.last_updated = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'expense': expense.to_dict(),
        'new_balance': account.balance,
        'card_updated': card_balance_updated
    })


@app.route('/api/expenses/variable/<int:expense_id>/delete', methods=['POST', 'DELETE'])
def delete_variable_expense(expense_id):
    """Delete a variable expense and reverse balance changes"""
    expense = VariableExpenseLog.query.get(expense_id)
    if not expense:
        return jsonify({'error': 'Expense not found'}), 404
    
    account = Account.query.first()
    card_balance_updated = None
    
    # Reverse the transaction
    if expense.card_id:
        # Was on card - remove from card balance
        card = Card.query.get(expense.card_id)
        if card:
            # Smart removal: try OPEN first (most common), then CLOSED
            statement_affected = 'OPEN'
            if card.open_balance >= expense.amount:
                card.open_balance -= expense.amount
            else:
                # Must be in closed balance
                card.closed_balance -= expense.amount
                statement_affected = 'CLOSED'
            
            card_balance_updated = {
                'card_name': card.name,
                'closed_balance': card.closed_balance,
                'open_balance': card.open_balance,
                'statement_affected': statement_affected,
                'expense_day': expense.expense_date.day,
                'closing_day': card.closing_day
            }
    else:
        # Was cash - add back to checking
        account.balance += expense.amount
    
    account.last_updated = datetime.utcnow()
    
    # Delete the expense
    db.session.delete(expense)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'new_balance': account.balance,
        'card_updated': card_balance_updated,
        'deleted_amount': expense.amount
    })


@app.route('/api/expenses/this-month', methods=['GET'])
def get_expenses_this_month():
    """Get all expenses paid/logged this month"""
    today = datetime.now()
    
    # Fixed expenses paid
    fixed_paid = ExpensePayment.query.filter_by(
        month=today.month,
        year=today.year
    ).all()
    
    # Variable expenses
    start_of_month = datetime(today.year, today.month, 1)
    variable_expenses = VariableExpenseLog.query.filter(
        VariableExpenseLog.expense_date >= start_of_month
    ).all()
    
    # Fixed expenses NOT yet paid
    all_fixed = FixedExpense.query.filter_by(active=True).all()
    paid_ids = {p.expense_id for p in fixed_paid}
    unpaid_fixed = [e for e in all_fixed if e.id not in paid_ids]
    
    # Card payments this month
    card_payments = CardPayment.query.filter(
        CardPayment.payment_date >= start_of_month
    ).all()
    
    return jsonify({
        'fixed_paid': [p.to_dict() for p in fixed_paid],
        'fixed_unpaid': [e.to_dict() for e in unpaid_fixed],
        'variable_expenses': [v.to_dict() for v in variable_expenses],
        'card_payments': [cp.to_dict() for cp in card_payments],
        'total_fixed_paid': sum(p.amount for p in fixed_paid),
        'total_variable': sum(v.amount for v in variable_expenses),
        'total_card_payments': sum(cp.amount for cp in card_payments)
    })


@app.route('/api/cards/pay', methods=['POST'])
def pay_credit_card():
    """Pay credit card from checking account"""
    data = request.json
    card_id = int(data['card_id'])
    amount = float(data['amount'])
    payment_date_str = data.get('payment_date')
    
    if payment_date_str:
        payment_date = datetime.fromisoformat(payment_date_str)
    else:
        payment_date = datetime.now()
    
    card = Card.query.get(card_id)
    if not card:
        return jsonify({'error': 'Card not found'}), 404
    
    account = Account.query.first()
    
    # Verify checking has enough balance
    if account.balance < amount:
        return jsonify({
            'error': f'Saldo insuficiente en checking (${account.balance:.2f})'
        }), 400
    
    # Create payment record
    payment = CardPayment(
        card_id=card_id,
        amount=amount,
        payment_date=payment_date,
        notes=data.get('notes', '')
    )
    
    # Update balances - first reduce closed_balance, then open_balance if excess
    remaining_payment = amount

    # First, apply payment to closed_balance
    if card.closed_balance > 0:
        if remaining_payment >= card.closed_balance:
            remaining_payment -= card.closed_balance
            card.closed_balance = 0
        else:
            card.closed_balance -= remaining_payment
            remaining_payment = 0

    # If there's remaining payment, apply to open_balance
    if remaining_payment > 0 and card.open_balance > 0:
        if remaining_payment >= card.open_balance:
            remaining_payment -= card.open_balance
            card.open_balance = 0
        else:
            card.open_balance -= remaining_payment
            remaining_payment = 0

    # Also update current_balance for legacy compatibility
    card.current_balance -= amount
    if card.current_balance < 0:
        card.current_balance = 0

    account.balance -= amount       # Deduct from checking
    account.last_updated = datetime.utcnow()
    
    db.session.add(payment)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'payment': payment.to_dict(),
        'new_card_balance': card.current_balance,
        'new_closed_balance': card.closed_balance,
        'new_open_balance': card.open_balance,
        'new_checking_balance': account.balance
    })


@app.route('/api/expenses/apple-pay', methods=['POST'])
@require_apple_pay_api_key
def add_apple_pay_expense():
    """
    Add expense from Apple Pay transaction via iOS Shortcuts.

    POST body:
    {
        "api_key": "your-api-key",
        "amount": 45.67,
        "card_name": "Apple Card",
        "merchant": "Starbucks",
        "transaction_date": "2026-01-21T10:30:00",
        "user": "Tak"  // optional - who made the purchase
    }

    Responses:
    - 201: Expense registered successfully
    - 202: Expense saved as pending (card not found, needs review)
    - 400: Bad request
    - 401: Invalid API key
    """
    try:
        data = request.json

        # Validate required fields
        if 'amount' not in data:
            return jsonify({'error': 'Amount is required'}), 400

        amount = abs(float(data['amount']))  # Ensure positive
        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400

        # Parse transaction date
        transaction_date_str = data.get('transaction_date')
        if transaction_date_str:
            try:
                transaction_date = datetime.fromisoformat(
                    transaction_date_str.replace('Z', '+00:00').replace('+00:00', '')
                )
            except ValueError:
                transaction_date = datetime.now()
        else:
            transaction_date = datetime.now()

        # Get other fields
        card_name = data.get('card_name', '')
        merchant = data.get('merchant', '')
        user = data.get('user', '')

        # Match card by name (with new alias system)
        card, match_type = match_card_by_name(card_name)

        # If card not found and card_name was provided, save as pending
        if not card and card_name:
            pending = PendingApplePayExpense(
                apple_card_name=card_name,
                amount=amount,
                merchant=merchant,
                user=user,
                transaction_date=transaction_date,
                status='pending'
            )
            db.session.add(pending)
            db.session.commit()

            available = [c.name for c in Card.query.all()]
            return jsonify({
                'success': True,
                'status': 'pending_review',
                'pending_id': pending.id,
                'message': f'Card "{card_name}" not recognized. Saved for review.',
                'available_cards': available,
                'expense_data': {
                    'amount': amount,
                    'merchant': merchant,
                    'user': user,
                    'transaction_date': transaction_date.isoformat()
                }
            }), 202

        # Auto-categorize by merchant
        category, category_source = categorize_by_merchant(merchant)

        # Build description with user info
        if merchant and user:
            description = f"{merchant} - {user} (Apple Pay)"
        elif merchant:
            description = f"{merchant} (Apple Pay)"
        elif user:
            description = f"Apple Pay - {user}"
        else:
            description = "Apple Pay Transaction"

        # Create expense
        expense = VariableExpenseLog(
            category=category,
            amount=amount,
            description=description,
            expense_date=transaction_date,
            card_id=card.id if card else None
        )

        account = Account.query.first()
        card_balance_updated = None

        # Update balances
        if card:
            # Card payment - add to open balance
            card.open_balance += amount
            card_balance_updated = {
                'card_name': card.name,
                'closed_balance': card.closed_balance,
                'open_balance': card.open_balance
            }
        else:
            # Cash/debit - deduct from checking
            if account:
                account.balance -= amount

        if account:
            account.last_updated = datetime.utcnow()

        db.session.add(expense)
        db.session.commit()

        # Index in RAG system (non-blocking)
        try:
            from rag.insights_engine import get_insights_engine
            engine = get_insights_engine()
            if engine:
                engine.index_expense(expense)
        except Exception as e:
            print(f"RAG indexing error (non-critical): {e}")

        return jsonify({
            'success': True,
            'status': 'registered',
            'expense': expense.to_dict(),
            'new_balance': account.balance if account else None,
            'card_updated': card_balance_updated,
            'match_type': match_type,
            'auto_categorized': True,
            'category_source': category_source,
            'user': user or None
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error adding Apple Pay expense: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# APPLE PAY PENDING & ALIASES MANAGEMENT
# ============================================================================

@app.route('/api/apple-pay/pending', methods=['GET'])
def get_pending_apple_pay():
    """Get all pending Apple Pay expenses that need review"""
    pending = PendingApplePayExpense.query.filter_by(status='pending').order_by(
        PendingApplePayExpense.created_at.desc()
    ).all()

    return jsonify({
        'count': len(pending),
        'pending': [p.to_dict() for p in pending],
        'available_cards': [{'id': c.id, 'name': c.name} for c in Card.query.all()]
    })


@app.route('/api/apple-pay/pending/<int:pending_id>/resolve', methods=['POST'])
def resolve_pending_apple_pay(pending_id):
    """
    Resolve a pending Apple Pay expense by assigning it to a card.

    POST body:
    {
        "card_id": 2,
        "create_alias": true  // optional, default true
    }
    """
    try:
        pending = PendingApplePayExpense.query.get(pending_id)
        if not pending:
            return jsonify({'error': 'Pending expense not found'}), 404

        if pending.status != 'pending':
            return jsonify({'error': f'Expense already {pending.status}'}), 400

        data = request.json or {}
        card_id = data.get('card_id')
        create_alias = data.get('create_alias', True)

        if not card_id:
            return jsonify({'error': 'card_id is required'}), 400

        card = Card.query.get(card_id)
        if not card:
            return jsonify({'error': 'Card not found'}), 404

        # Auto-categorize by merchant
        category, category_source = categorize_by_merchant(pending.merchant)

        # Build description
        if pending.merchant and pending.user:
            description = f"{pending.merchant} - {pending.user} (Apple Pay)"
        elif pending.merchant:
            description = f"{pending.merchant} (Apple Pay)"
        elif pending.user:
            description = f"Apple Pay - {pending.user}"
        else:
            description = "Apple Pay Transaction"

        # Create the expense
        expense = VariableExpenseLog(
            category=category,
            amount=pending.amount,
            description=description,
            expense_date=pending.transaction_date,
            card_id=card.id
        )

        # Update card balance
        card.open_balance += pending.amount

        # Update pending record
        pending.status = 'resolved'
        pending.resolved_card_id = card.id
        pending.resolved_at = datetime.utcnow()

        db.session.add(expense)
        db.session.commit()

        # Link expense to pending record
        pending.resolved_expense_id = expense.id
        db.session.commit()

        # Create alias for future transactions
        alias_created = None
        if create_alias:
            existing_alias = CardAlias.query.filter(
                db.func.lower(CardAlias.apple_name) == pending.apple_card_name.lower()
            ).first()

            if not existing_alias:
                new_alias = CardAlias(
                    apple_name=pending.apple_card_name,
                    card_id=card.id
                )
                db.session.add(new_alias)
                db.session.commit()
                alias_created = new_alias.to_dict()

        return jsonify({
            'success': True,
            'expense': expense.to_dict(),
            'card_updated': {
                'card_name': card.name,
                'closed_balance': card.closed_balance,
                'open_balance': card.open_balance
            },
            'alias_created': alias_created,
            'message': f'Expense resolved and assigned to {card.name}'
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error resolving pending expense: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/apple-pay/pending/<int:pending_id>/ignore', methods=['POST'])
def ignore_pending_apple_pay(pending_id):
    """Mark a pending Apple Pay expense as ignored (won't be processed)"""
    pending = PendingApplePayExpense.query.get(pending_id)
    if not pending:
        return jsonify({'error': 'Pending expense not found'}), 404

    if pending.status != 'pending':
        return jsonify({'error': f'Expense already {pending.status}'}), 400

    pending.status = 'ignored'
    pending.resolved_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Expense ignored'
    })


@app.route('/api/apple-pay/aliases', methods=['GET'])
def get_card_aliases():
    """Get all card aliases"""
    aliases = CardAlias.query.order_by(CardAlias.created_at.desc()).all()

    return jsonify({
        'count': len(aliases),
        'aliases': [a.to_dict() for a in aliases],
        'available_cards': [{'id': c.id, 'name': c.name} for c in Card.query.all()]
    })


@app.route('/api/apple-pay/aliases', methods=['POST'])
def create_card_alias():
    """
    Create a new card alias manually.

    POST body:
    {
        "apple_name": "Chase Sapphire Reserve",
        "card_id": 3
    }
    """
    try:
        data = request.json
        apple_name = data.get('apple_name', '').strip()
        card_id = data.get('card_id')

        if not apple_name:
            return jsonify({'error': 'apple_name is required'}), 400
        if not card_id:
            return jsonify({'error': 'card_id is required'}), 400

        # Check if alias already exists
        existing = CardAlias.query.filter(
            db.func.lower(CardAlias.apple_name) == apple_name.lower()
        ).first()
        if existing:
            return jsonify({
                'error': f'Alias "{apple_name}" already exists',
                'existing_alias': existing.to_dict()
            }), 400

        card = Card.query.get(card_id)
        if not card:
            return jsonify({'error': 'Card not found'}), 404

        alias = CardAlias(
            apple_name=apple_name,
            card_id=card_id
        )
        db.session.add(alias)
        db.session.commit()

        return jsonify({
            'success': True,
            'alias': alias.to_dict(),
            'message': f'Alias created: "{apple_name}" -> {card.name}'
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/apple-pay/aliases/<int:alias_id>', methods=['DELETE'])
def delete_card_alias(alias_id):
    """Delete a card alias"""
    alias = CardAlias.query.get(alias_id)
    if not alias:
        return jsonify({'error': 'Alias not found'}), 404

    apple_name = alias.apple_name
    db.session.delete(alias)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Alias "{apple_name}" deleted'
    })


@app.route('/api/cards/add', methods=['POST'])
def add_card():
    """Add a new credit card"""
    try:
        data = request.json
        
        # Validate required fields
        required = ['name', 'credit_limit', 'closing_day', 'payment_due_day']
        for field in required:
            if field not in data or not data[field]:
                return jsonify({'error': f'Campo requerido: {field}'}), 400
        
        # Check if card name already exists
        existing = Card.query.filter_by(name=data['name']).first()
        if existing:
            return jsonify({'error': f'Ya existe una tarjeta con el nombre "{data["name"]}"'}), 400
        
        # Determine if balance is closed or open (legacy)
        balance_is_closed = False
        if data.get('current_balance', 0) > 0:
            balance_is_closed = data.get('balance_statement_type') == 'closed'
        
        # Create new card
        card = Card(
            name=data['name'],
            credit_limit=float(data['credit_limit']),
            current_balance=float(data.get('current_balance', 0)),  # Legacy
            balance_is_closed=balance_is_closed,  # Legacy
            closed_balance=float(data.get('closed_balance', 0)),  # New
            open_balance=float(data.get('open_balance', 0)),  # New
            closing_day=int(data['closing_day']),
            payment_due_day=int(data['payment_due_day']),
            apr=float(data.get('apr', 0))
        )
        
        db.session.add(card)
        db.session.commit()
        
        # Refresh to get the ID
        db.session.refresh(card)
        
        return jsonify({
            'success': True,
            'card': card.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error adding card: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error al guardar tarjeta: {str(e)}'}), 500


@app.route('/api/cards/<int:card_id>/edit', methods=['PUT'])
def edit_card(card_id):
    """Edit an existing credit card"""
    try:
        card = Card.query.get(card_id)
        if not card:
            return jsonify({'error': 'Tarjeta no encontrada'}), 404
        
        data = request.json
        
        # Update fields if provided
        if 'name' in data:
            # Check if new name conflicts with another card
            existing = Card.query.filter(Card.name == data['name'], Card.id != card_id).first()
            if existing:
                return jsonify({'error': f'Ya existe otra tarjeta con el nombre "{data["name"]}"'}), 400
            card.name = data['name']
        
        if 'credit_limit' in data:
            card.credit_limit = float(data['credit_limit'])
        
        # New dual balance system
        if 'closed_balance' in data:
            card.closed_balance = float(data['closed_balance'])
        
        if 'open_balance' in data:
            card.open_balance = float(data['open_balance'])
        
        # Legacy balance handling (for backwards compatibility)
        if 'current_balance' in data:
            card.current_balance = float(data['current_balance'])
            if 'balance_statement_type' in data:
                card.balance_is_closed = (data['balance_statement_type'] == 'closed')
        
        if 'closing_day' in data:
            card.closing_day = int(data['closing_day'])
        
        if 'payment_due_day' in data:
            card.payment_due_day = int(data['payment_due_day'])
        
        if 'apr' in data:
            card.apr = float(data['apr'])
        
        # Handle manual payment date
        if 'manual_payment_date' in data:
            if data['manual_payment_date']:
                from datetime import datetime
                card.manual_payment_date = datetime.fromisoformat(data['manual_payment_date']).date()
            else:
                card.manual_payment_date = None
        
        db.session.commit()
        db.session.refresh(card)
        
        return jsonify({
            'success': True,
            'card': card.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error editing card: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error al editar tarjeta: {str(e)}'}), 500


@app.route('/api/cards/<int:card_id>/delete', methods=['DELETE'])
def delete_card(card_id):
    """Delete a credit card (only if no expenses or payments associated)"""
    card = Card.query.get(card_id)
    if not card:
        return jsonify({'error': 'Tarjeta no encontrada'}), 404
    
    # Check if card has associated expenses
    var_expenses_count = VariableExpenseLog.query.filter_by(card_id=card_id).count()
    payments_count = CardPayment.query.filter_by(card_id=card_id).count()
    
    if var_expenses_count > 0 or payments_count > 0:
        return jsonify({
            'error': f'No se puede eliminar. La tarjeta tiene {var_expenses_count} gastos y {payments_count} pagos registrados.',
            'suggestion': 'Puedes editar la tarjeta en su lugar.'
        }), 400
    
    db.session.delete(card)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Tarjeta "{card.name}" eliminada correctamente'
    })


# Expense Category Management
@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all expense categories"""
    categories = ExpenseCategory.query.order_by(ExpenseCategory.name).all()
    return jsonify({
        'categories': [c.to_dict() for c in categories]
    })


@app.route('/api/categories/add', methods=['POST'])
def add_category():
    """Add a new expense category"""
    data = request.json
    name = data.get('name', '').strip()
    icon = data.get('icon', '📌')
    
    if not name:
        return jsonify({'error': 'Category name is required'}), 400
    
    # Check if already exists
    existing = ExpenseCategory.query.filter_by(name=name).first()
    if existing:
        return jsonify({'error': 'Category already exists'}), 400
    
    category = ExpenseCategory(name=name, icon=icon)
    db.session.add(category)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'category': category.to_dict()
    })


@app.route('/api/categories/<int:category_id>/delete', methods=['POST'])
def delete_category(category_id):
    """Delete an expense category"""
    category = ExpenseCategory.query.get(category_id)
    if not category:
        return jsonify({'error': 'Category not found'}), 404

    # Check if any expenses use this category
    expenses_count = VariableExpenseLog.query.filter_by(category=category.name).count()
    if expenses_count > 0:
        return jsonify({
            'error': f'Cannot delete. {expenses_count} expenses use this category.'
        }), 400

    db.session.delete(category)
    db.session.commit()

    return jsonify({'success': True})


# ============================================================================
# RAG INSIGHTS ENDPOINTS
# ============================================================================

# Lazy-loaded insights engine
_insights_engine = None

def get_insights_engine():
    """Get or create the insights engine instance"""
    global _insights_engine
    if _insights_engine is None:
        try:
            from rag import InsightsEngine
            _insights_engine = InsightsEngine()
        except ImportError as e:
            print(f"RAG module not available: {e}")
            return None
    return _insights_engine


@app.route('/api/rag/status', methods=['GET'])
def rag_status():
    """Get RAG system status"""
    engine = get_insights_engine()
    if not engine:
        return jsonify({
            'available': False,
            'error': 'RAG module not installed. Run: pip install anthropic chromadb sentence-transformers'
        })

    status = engine.get_status()
    return jsonify({
        'available': True,
        **status
    })


@app.route('/api/insights/spending-analysis', methods=['GET'])
def get_spending_analysis():
    """
    Get AI-powered spending analysis

    Query params:
    - period: 'week', 'month', '3months' (default: 'month')
    - category: optional category filter
    """
    engine = get_insights_engine()
    if not engine:
        return jsonify({'error': 'RAG system not available'}), 503

    if not engine.is_configured():
        return jsonify({
            'error': 'RAG not configured. Set ANTHROPIC_API_KEY in .env file'
        }), 503

    period = request.args.get('period', 'month')
    category = request.args.get('category')

    result = engine.analyze_spending(period=period, category=category)
    return jsonify(result)


@app.route('/api/insights/optimization-suggestions', methods=['GET'])
def get_optimization_suggestions():
    """Get AI-powered optimization suggestions"""
    engine = get_insights_engine()
    if not engine:
        return jsonify({'error': 'RAG system not available'}), 503

    if not engine.is_configured():
        return jsonify({
            'error': 'RAG not configured. Set ANTHROPIC_API_KEY in .env file'
        }), 503

    result = engine.get_optimization_suggestions()
    return jsonify(result)


@app.route('/api/insights/best-savings-time', methods=['GET'])
def get_best_savings_time():
    """Get recommendation for best time to transfer to savings"""
    engine = get_insights_engine()
    if not engine:
        return jsonify({'error': 'RAG system not available'}), 503

    if not engine.is_configured():
        return jsonify({
            'error': 'RAG not configured. Set ANTHROPIC_API_KEY in .env file'
        }), 503

    result = engine.get_best_savings_time()
    return jsonify(result)


@app.route('/api/insights/category/<category_name>', methods=['GET'])
def get_category_insight(category_name):
    """Get detailed insight for a specific category"""
    engine = get_insights_engine()
    if not engine:
        return jsonify({'error': 'RAG system not available'}), 503

    if not engine.is_configured():
        return jsonify({
            'error': 'RAG not configured. Set ANTHROPIC_API_KEY in .env file'
        }), 503

    result = engine.get_category_insight(category_name)
    return jsonify(result)


@app.route('/api/insights/anomalies', methods=['GET'])
def get_anomalies():
    """Detect and explain spending anomalies"""
    engine = get_insights_engine()
    if not engine:
        return jsonify({'error': 'RAG system not available'}), 503

    if not engine.is_configured():
        return jsonify({
            'error': 'RAG not configured. Set ANTHROPIC_API_KEY in .env file'
        }), 503

    result = engine.detect_anomalies()
    return jsonify(result)


@app.route('/api/insights/chat', methods=['POST'])
def chat_with_finances():
    """
    Chat conversationally about finances with full context
    """
    engine = get_insights_engine()
    if not engine:
        return jsonify({'error': 'RAG system not available'}), 503

    if not engine.is_configured():
        return jsonify({
            'error': 'RAG not configured. Set ANTHROPIC_API_KEY in .env file'
        }), 503

    data = request.json
    message = data.get('message', '')
    history = data.get('conversation_history', [])

    if not message:
        return jsonify({'error': 'Message is required'}), 400

    # Get current financial context from database
    account = Account.query.first()
    savings_account = SavingsAccount.query.first()
    savings_goal = SavingsGoal.query.first()
    income = IncomeSchedule.query.first()
    cards = Card.query.all()
    fixed_expenses = FixedExpense.query.filter_by(active=True).all()

    # Calculate this month's data
    today = datetime.now()
    month_start = datetime(today.year, today.month, 1).date()

    # Variable expenses this month
    var_expenses = VariableExpenseLog.query.filter(
        VariableExpenseLog.expense_date >= month_start
    ).all()
    total_var = sum(e.amount for e in var_expenses)

    # Category breakdown
    cat_totals = {}
    for e in var_expenses:
        cat = e.category or 'Otros'
        cat_totals[cat] = cat_totals.get(cat, 0) + e.amount

    # Card payments this month
    card_payments_month = CardPayment.query.filter(
        CardPayment.payment_date >= month_start
    ).all()
    total_card_payments = sum(p.amount for p in card_payments_month)

    # Fixed expenses paid this month
    paid_fixed = ExpensePayment.query.filter(
        ExpensePayment.payment_month == today.month,
        ExpensePayment.payment_year == today.year
    ).all()
    paid_fixed_ids = [p.expense_id for p in paid_fixed]

    # Build current context
    cards_info = []
    for c in cards:
        card_data = c.to_dict()
        cards_info.append(
            f"- {c.name}: Límite ${c.credit_limit:,.0f}, "
            f"Balance cerrado ${card_data['closed_statement']['balance']:,.2f} "
            f"(vence {card_data['closed_statement']['payment_date']}), "
            f"Balance abierto ${card_data['open_statement']['balance']:,.2f} "
            f"(cierra {card_data['open_statement']['close_date']})"
        )

    fixed_info = []
    for f in fixed_expenses:
        status = "PAGADO" if f.id in paid_fixed_ids else "PENDIENTE"
        fixed_info.append(f"- {f.name}: ${f.amount:.2f} día {f.due_day} [{status}]")

    cat_info = [f"- {cat}: ${amt:.2f}" for cat, amt in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)]

    # Calculate savings status
    savings_this_month = 0  # TODO: track actual transfers
    savings_goal_amt = savings_goal.amount_per_paycheck if savings_goal else 500
    min_balance = savings_goal.min_balance_comfort if savings_goal else 2000

    current_context = f"""ESTADO FINANCIERO ACTUAL (Hoy: {today.strftime('%d/%m/%Y')}):

CUENTAS:
- Cuenta de cheques: ${account.balance:,.2f}
- Fondo de emergencia: ${savings_account.balance:,.2f} / ${savings_account.target:,.2f}
- Balance mínimo de confort: ${min_balance:,.2f}

INGRESOS:
- Catorcena: ${income.amount:,.2f} (días {income.first_paycheck_day} y {income.second_paycheck_day})

TARJETAS DE CRÉDITO:
{chr(10).join(cards_info)}

GASTOS FIJOS ESTE MES:
{chr(10).join(fixed_info)}
Total fijos: ${sum(f.amount for f in fixed_expenses):,.2f}

GASTOS VARIABLES ESTE MES: ${total_var:,.2f}
{chr(10).join(cat_info) if cat_info else '- Sin gastos registrados'}

PAGOS DE TARJETAS ESTE MES: ${total_card_payments:,.2f}

META DE AHORRO: ${savings_goal_amt:,.2f} por catorcena"""

    result = engine.chat(
        message=message,
        conversation_history=history,
        current_context=current_context
    )
    return jsonify(result)


@app.route('/api/rag/reindex', methods=['POST'])
def reindex_rag():
    """Reindex all data in ChromaDB (admin operation)"""
    engine = get_insights_engine()
    if not engine:
        return jsonify({'error': 'RAG system not available'}), 503

    # Get all data from SQLAlchemy (within Flask context)
    expenses = VariableExpenseLog.query.all()
    fixed_expenses = FixedExpense.query.filter_by(active=True).all()
    card_payments = CardPayment.query.all()
    income = IncomeSchedule.query.first()
    account = Account.query.first()
    savings = SavingsAccount.query.first()

    # Index expenses
    expense_result = engine.index_expenses_batch(expenses)

    # Update monthly summary
    month = datetime.now().strftime('%Y-%m')
    engine.update_monthly_summary(
        month=month,
        variable_expenses=expenses,
        fixed_expenses=fixed_expenses,
        card_payments=card_payments,
        income_amount=income.amount * 2 if income else 0,
        checking_balance=account.balance if account else 0,
        savings_balance=savings.balance if savings else 0
    )

    return jsonify({
        'success': True,
        'results': {
            'expenses': expense_result,
            'summaries': {'success': True},
            'patterns': {'count': 0}
        }
    })


@app.route('/api/rag/index-expense', methods=['POST'])
def index_single_expense():
    """Index a single expense (called automatically when adding expenses)"""
    engine = get_insights_engine()
    if not engine:
        return jsonify({'error': 'RAG system not available'}), 503

    data = request.json
    expense_id = data.get('expense_id')

    if not expense_id:
        return jsonify({'error': 'expense_id is required'}), 400

    expense = VariableExpenseLog.query.get(expense_id)
    if not expense:
        return jsonify({'error': 'Expense not found'}), 404

    success = engine.index_expense(expense)
    return jsonify({'success': success})


# Initialize WAL mode when the module is loaded (for Gunicorn workers)
with app.app_context():
    db.create_all()
    enable_wal_mode()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8081)
