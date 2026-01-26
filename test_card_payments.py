#!/usr/bin/env python3
"""
Simple test: Are card payments being calculated?
"""
from datetime import datetime
from app import app, db, Card

with app.app_context():
    cards = Card.query.all()
    purchase_date = datetime(2026, 1, 10)
    
    print("=" * 60)
    print("CARD PAYMENTS TEST")
    print("=" * 60)
    print(f"\nPurchase date: {purchase_date.date()}")
    print(f"\nChecking cards for closed statements...")
    
    card_payments = []
    for card in cards:
        card_dict = card.to_dict()
        print(f"\n{card.name}:")
        
        closed_statement = card_dict.get('closed_statement', {})
        print(f"  Has closed statement: {bool(closed_statement)}")
        
        if closed_statement:
            balance = closed_statement.get('balance', 0)
            payment_date_str = closed_statement.get('payment_date')
            print(f"  Balance: ${balance:,.2f}")
            print(f"  Payment date string: {payment_date_str}")
            
            if balance > 0 and payment_date_str:
                pmt_date = datetime.fromisoformat(payment_date_str).date()
                days_until = (pmt_date - purchase_date.date()).days
                print(f"  Payment date parsed: {pmt_date}")
                print(f"  Days until payment: {days_until}")
                
                if 0 <= days_until <= 30:
                    print(f"  ✅ INCLUDED (within 30 days)")
                    card_payments.append({
                        'card': card.name,
                        'amount': balance,
                        'date': pmt_date
                    })
                else:
                    print(f"  ❌ EXCLUDED (outside 30 day window)")
            else:
                print(f"  ❌ No balance or payment date")
    
    print("\n" + "=" * 60)
    print("RESULT:")
    print("=" * 60)
    
    if card_payments:
        print(f"\nFound {len(card_payments)} payments:")
        total = 0
        for p in card_payments:
            print(f"  • {p['card']}: ${p['amount']:,.2f} on {p['date']}")
            total += p['amount']
        print(f"\nTotal: ${total:,.2f}")
    else:
        print("\n❌ NO CARD PAYMENTS FOUND!")
        print("\nPossible reasons:")
        print("1. No cards have closed statements")
        print("2. All payment dates are outside 30-day window")
        print("3. Card data is not in database")
    
    print("=" * 60)
