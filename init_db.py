"""
Initialize database with Polo's actual data
"""

from app import app, db, Card, Account, SavingsAccount, IncomeSchedule, FixedExpense, SavingsGoal, BonusEvent
from datetime import datetime


def init_database():
    """Initialize database with Polo's configuration"""
    
    with app.app_context():
        # Drop all tables and recreate
        db.drop_all()
        db.create_all()
        
        print("🗄️  Database created")
        
        # ============================================================================
        # CARDS
        # ============================================================================
        
        bofa = Card(
            name='BofA',
            closing_day=19,
            payment_due_day=24,  # Payment on day 24 of next month
            credit_limit=20000,
            current_balance=0,  # Polo confirmed this is at $0
            apr=0
        )
        
        amex = Card(
            name='Amex',
            closing_day=2,  # Changed from 11 to 2 (Feb onwards)
            payment_due_day=27,  # Payment on day 27 of next month
            credit_limit=20000,
            current_balance=1346.66,
            apr=0
        )
        
        citi = Card(
            name='Citi',
            closing_day=26,
            payment_due_day=23,  # Payment on day 23 of next month
            credit_limit=20000,
            current_balance=2452.11,
            apr=0
        )
        
        db.session.add_all([bofa, amex, citi])
        print("💳 Cards added: BofA, Amex, Citi")
        
        # ============================================================================
        # ACCOUNTS
        # ============================================================================
        
        checking = Account(
            balance=5552.00,
            last_updated=datetime(2025, 12, 31)
        )
        db.session.add(checking)
        print("🏦 Checking account: $5,552")
        
        savings = SavingsAccount(
            balance=7000.00,
            target=15000.00,
            last_updated=datetime(2025, 12, 31)
        )
        db.session.add(savings)
        print("💰 Emergency fund: $7,000 / $15,000")
        
        # ============================================================================
        # INCOME SCHEDULE
        # ============================================================================
        
        income = IncomeSchedule(
            amount=3300.00,
            first_paycheck_day=9,
            second_paycheck_day=23
        )
        db.session.add(income)
        print("📅 Income: $3,300 on days 9 and 23")
        
        # ============================================================================
        # FIXED EXPENSES - POLO'S REAL DATA
        # ============================================================================
        
        rent = FixedExpense(
            name='Renta',
            amount=3100.00,
            due_day=1,
            category='Housing',
            active=True
        )
        
        subscriptions = FixedExpense(
            name='Subscripciones',
            amount=80.00,
            due_day=5,
            category='Subscriptions',
            active=True
        )
        
        insurance = FixedExpense(
            name='Seguros',
            amount=266.29,
            due_day=10,
            category='Insurance',
            active=True
        )
        
        phone = FixedExpense(
            name='Teléfono',
            amount=25.00,
            due_day=15,
            category='Utilities',
            active=True
        )
        
        internet = FixedExpense(
            name='Internet',
            amount=75.00,
            due_day=20,
            category='Utilities',
            active=True
        )
        
        gas_luz = FixedExpense(
            name='Gas - Luz',
            amount=290.00,
            due_day=25,
            category='Utilities',
            active=True
        )
        
        car_lease = FixedExpense(
            name='Leasing Coche',
            amount=650.00,
            due_day=5,
            category='Transportation',
            active=True
        )
        
        db.session.add_all([rent, subscriptions, insurance, phone, internet, gas_luz, car_lease])
        print("📋 Fixed expenses added: $4,486.29/month")
        
        # ============================================================================
        # SAVINGS GOAL - POLO'S STRATEGY
        # ============================================================================
        
        savings_goal = SavingsGoal(
            amount_per_paycheck=500.00,  # Moderate strategy
            min_balance_comfort=2000.00,  # Polo's comfort zone
            variable_expenses_monthly=240.00  # Polo's real variable expenses
        )
        db.session.add(savings_goal)
        print("🎯 Savings goal: $500/paycheck | Min balance: $2,000 | Variables: $240/month")
        
        # ============================================================================
        # BONUS EVENTS
        # ============================================================================
        
        march_bonus = BonusEvent(
            amount=5000.00,
            expected_date=datetime(2026, 3, 15),
            description='Q1 Bonus',
            received=False
        )
        db.session.add(march_bonus)
        print("🎁 Bonus scheduled: $5,000 in March 2026")
        
        # Commit all changes
        db.session.commit()
        
        print("\n✅ Database initialized successfully!")
        print("\n📊 CURRENT STATUS:")
        print(f"   Checking: ${checking.balance:,.2f}")
        print(f"   Savings: ${savings.balance:,.2f} / ${savings.target:,.2f} ({savings.balance/savings.target*100:.1f}%)")
        print(f"   Cards: BofA=$0 | Amex=${amex.current_balance:,.2f} | Citi=${citi.current_balance:,.2f}")
        print(f"\n💰 MONTHLY BUDGET:")
        print(f"   Fixed expenses: $4,486.29")
        print(f"   Variable expenses: $240.00")
        print(f"   Total expenses: $4,726.29")
        print(f"   Monthly income: $6,600.00")
        print(f"   Available for savings: $1,873.71/month")
        print(f"\n🎯 SAVINGS PROJECTION:")
        print(f"   Current: $7,000")
        print(f"   Goal per paycheck: $500 ($1,000/month)")
        print(f"   March bonus: +$5,000")
        print(f"   Estimated to reach $15k: Jun 2026")


if __name__ == '__main__':
    init_database()
