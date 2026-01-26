"""
Quick test of recommendation engine
"""

from app import app, db, Card, Account, IncomeSchedule, SavingsGoal
from recommendation_engine import CardRecommendationEngine
from datetime import datetime

with app.app_context():
    # Get data
    cards = Card.query.filter_by(active=True).all()
    account = Account.query.first()
    income = IncomeSchedule.query.first()
    savings_goal = SavingsGoal.query.first()
    
    print("=" * 70)
    print("🧪 TESTING RECOMMENDATION ENGINE")
    print("=" * 70)
    print(f"\n📊 Current State:")
    print(f"   Checking Balance: ${account.balance:,.2f}")
    print(f"   Cards: {len(cards)}")
    for card in cards:
        print(f"   - {card.name}: ${card.current_balance:,.2f} / ${card.credit_limit:,.2f} ({card.current_balance/card.credit_limit*100:.1f}%)")
    
    # Test recommendation
    print(f"\n🔍 Testing recommendation for $500 purchase today...")
    
    engine = CardRecommendationEngine(
        cards=cards,
        current_balance=account.balance,
        income_schedule=income,
        savings_goal=savings_goal
    )
    
    recommendations = engine.recommend(500.00, datetime.now())
    
    print(f"\n🎯 RECOMMENDATIONS:\n")
    
    for i, rec in enumerate(recommendations, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
        print(f"{medal} #{i} {rec.card.name} - Score: {rec.total_score:.1f}/100")
        print(f"   Payment Date: {rec.payment_date.strftime('%Y-%m-%d')}")
        print(f"   Projected Balance: ${rec.projected_balance:,.2f}")
        print(f"   Breakdown:")
        print(f"     • Timing:       {rec.timing_score:.1f}/35  ({rec.timing_score/35*100:.0f}%)")
        print(f"     • Liquidity:    {rec.liquidity_score:.1f}/25  ({rec.liquidity_score/25*100:.0f}%)")
        print(f"     • Savings:      {rec.savings_impact_score:.1f}/15  ({rec.savings_impact_score/15*100:.0f}%)")
        print(f"     • Utilization:  {rec.utilization_score:.1f}/15  ({rec.utilization_score/15*100:.0f}%)")
        print(f"     • Distribution: {rec.distribution_score:.1f}/10  ({rec.distribution_score/10*100:.0f}%)")
        print(f"   Reasoning: {rec.reasoning}")
        print()
    
    print("=" * 70)
    print("✅ Test completed successfully!")
    print("=" * 70)
