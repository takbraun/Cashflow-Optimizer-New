#!/usr/bin/env python3
"""
Debug script to test liquidity calculation
Run this to verify the algorithm is working correctly
"""
from datetime import datetime
from app import app, db, Card, Account, IncomeSchedule, SavingsGoal, FixedExpense
from recommendation_engine import CardRecommendationEngine

with app.app_context():
    # Get data
    cards = Card.query.all()
    account = Account.query.first()
    income = IncomeSchedule.query.first()
    savings_goal = SavingsGoal.query.first()
    fixed_expenses = FixedExpense.query.filter_by(active=True).all()
    
    print("=" * 60)
    print("LIQUIDITY CALCULATION DEBUG")
    print("=" * 60)
    
    # Test data
    purchase_amount = 100
    purchase_date = datetime(2026, 1, 10)  # 10 Enero
    today = datetime.now()
    
    print(f"\nToday: {today.date()} {today.time()}")
    print(f"Purchase date: {purchase_date.date()}")
    print(f"Amount: ${purchase_amount}")
    
    # Calculate card payments
    card_payments = []
    for card in cards:
        card_dict = card.to_dict()
        prev_statement = card_dict.get('previous_statement', {})
        if prev_statement.get('balance', 0) > 0:
            payment_date_str = prev_statement.get('payment_date')
            if payment_date_str:
                pmt_date = datetime.fromisoformat(payment_date_str).date()
                days_until = (pmt_date - purchase_date.date()).days
                if 0 <= days_until <= 30:
                    card_payments.append({
                        'card': card.name,
                        'amount': prev_statement['balance'],
                        'date': pmt_date,
                        'days': days_until
                    })
    
    total_card_payments = sum(p['amount'] for p in card_payments)
    
    print(f"\n--- Card Payments (next 30 days from purchase) ---")
    for p in card_payments:
        print(f"  {p['card']}: ${p['amount']:,.2f} on {p['date']} (in {p['days']} days)")
    print(f"  Total: ${total_card_payments:,.2f}")
    
    # Setup engine
    fixed_monthly = sum(e.amount for e in fixed_expenses)
    rent_amount = max([e.amount for e in fixed_expenses], default=0)
    
    engine = CardRecommendationEngine(
        cards=cards,
        current_balance=account.balance,
        income_schedule=income,
        savings_goal=savings_goal
    )
    engine.rent_amount = rent_amount
    engine.fixed_expenses_monthly = fixed_monthly
    engine.card_payments_this_month = card_payments
    
    print(f"\n--- Fixed Data ---")
    print(f"Checking balance: ${account.balance:,.2f}")
    print(f"Fixed expenses/month: ${fixed_monthly:,.2f}")
    print(f"Variable expenses/month: ${savings_goal.variable_expenses_monthly:,.2f}")
    print(f"Income per paycheck: ${income.amount:,.2f}")
    
    # Test projection
    projected = engine._project_balance(purchase_date)
    print(f"\n--- Projection to {purchase_date.date()} ---")
    days = (purchase_date - today).days
    print(f"Days: {days}")
    print(f"Projected balance: ${projected:,.2f}")
    
    # Test liquidity check
    result = engine._check_liquidity(
        purchase_amount=purchase_amount,
        purchase_date=purchase_date,
        is_deferred=False,
        payment_per_installment=purchase_amount,
        num_payments=1,
        payment_frequency='once'
    )
    
    print(f"\n--- Liquidity Analysis ---")
    print(f"Status: {result['status_emoji']} {result['status_text']}")
    print(f"Available after obligations: ${result['available_after_obligations']:,.2f}")
    print(f"Remaining after purchase: ${result['remaining_after_purchase']:,.2f}")
    
    if result.get('warning'):
        print(f"\nWarning: {result['warning']}")
    
    print("\n" + "=" * 60)
    
    # Expected result
    print("\nEXPECTED RESULT:")
    print("Status: 🔴 Esperar")
    print("Remaining: Around -$670 to -$770")
    print("=" * 60)
