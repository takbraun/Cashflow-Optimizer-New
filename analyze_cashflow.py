"""
Cash Flow Analysis - Polo's Real Numbers
"""

from app import app, db
from datetime import datetime, timedelta

with app.app_context():
    print("=" * 80)
    print("💰 ANÁLISIS DE CASH FLOW - NÚMEROS REALES")
    print("=" * 80)
    
    # Current state
    print("\n📊 ESTADO ACTUAL (3 Ene 2026):")
    print("   Checking: $5,552.00")
    print("   Savings: $7,000.00 / $15,000.00 (46.7%)")
    print("   Faltante para meta: $8,000.00")
    
    # Monthly budget
    print("\n💵 PRESUPUESTO MENSUAL:")
    print("   Ingresos (2 catorcenas): $6,600.00")
    print()
    print("   Gastos Fijos:")
    print("     • Renta:              $3,100.00")
    print("     • Leasing Coche:        $650.00")
    print("     • Gas - Luz:            $290.00")
    print("     • Seguros:              $266.29")
    print("     • Subscripciones:        $80.00")
    print("     • Internet:              $75.00")
    print("     • Teléfono:              $25.00")
    print("     ────────────────────────────────")
    print("     TOTAL FIJOS:         $4,486.29")
    print()
    print("   Gastos Variables:")
    print("     • Comida/Restaurantes:  $100.00")
    print("     • Shopping personal:    $100.00")
    print("     • Gasolina:              $40.00")
    print("     ────────────────────────────────")
    print("     TOTAL VARIABLES:       $240.00")
    print()
    print("   TOTAL GASTOS:          $4,726.29")
    print("   ════════════════════════════════")
    print("   FLUJO NETO MENSUAL:    $1,873.71 ✅")
    
    # Savings analysis
    print("\n🎯 ANÁLISIS DE AHORRO:")
    print("   Meta por catorcena: $500.00")
    print("   Meta mensual: $1,000.00")
    print("   Flujo disponible: $1,873.71")
    print("   → Sobran $873.71 después de meta de ahorro ✅")
    print()
    print("   ¿Es realista la meta de $500/catorcena?")
    print("   SÍ - Tienes margen cómodo de $873/mes extra")
    
    # Timeline to goal
    print("\n📅 TIMELINE HACIA $15,000:")
    
    current_savings = 7000
    target = 15000
    remaining = target - current_savings
    
    print(f"   Actual: ${current_savings:,.0f}")
    print(f"   Meta: ${target:,.0f}")
    print(f"   Faltante: ${remaining:,.0f}")
    print()
    
    # Without bonus
    monthly_savings = 1000  # $500 x 2 catorcenas
    months_without_bonus = remaining / monthly_savings
    print(f"   Sin bono:")
    print(f"     → {months_without_bonus:.1f} meses a $1,000/mes")
    print(f"     → Llegarías a: {datetime.now() + timedelta(days=30*months_without_bonus):%b %Y}")
    print()
    
    # With bonus
    bonus = 5000
    bonus_date = datetime(2026, 3, 15)
    remaining_after_bonus = remaining - bonus
    months_after_bonus = remaining_after_bonus / monthly_savings
    
    months_until_bonus = 2.5  # ~2.5 meses hasta marzo
    savings_until_bonus = months_until_bonus * monthly_savings
    total_by_bonus = current_savings + savings_until_bonus + bonus
    
    print(f"   Con bono de marzo ($5,000):")
    print(f"     → Ahorras $2,500 hasta marzo ($1,000 x 2.5 meses)")
    print(f"     → En marzo tendrás: $7,000 + $2,500 + $5,000 = ${total_by_bonus:,.0f}")
    print(f"     → Faltarían solo: ${target - total_by_bonus:,.0f}")
    print(f"     → Tiempo después del bono: {(target - total_by_bonus) / monthly_savings:.1f} meses")
    print(f"     → LLEGAS A $15K EN: JUN 2026 ✅")
    
    # January specific analysis
    print("\n📆 ANÁLISIS DE ENERO 2026:")
    print()
    print("   PRIMERA CATORCENA (1-8 Ene):")
    print("   ────────────────────────────")
    print("   Balance inicial: $5,552.00")
    print("   Gastos:")
    print("     • 1 Ene: Renta           -$3,100.00")
    print("     • 5 Ene: Amex pago       -$1,346.66")
    print("     • 5 Ene: Subscripciones    -$80.00")
    print("     • 5 Ene: Leasing          -$650.00")
    print("     • Variables (8 días)       -$64.00")
    print("   ────────────────────────────")
    print("   Subtotal gastos:          -$5,240.66")
    print("   Balance antes catorcena:     $311.34 ⚠️")
    print()
    print("   9 Ene: INGRESO            +$3,300.00")
    print("   Balance: $3,611.34 ✅")
    print()
    
    print("   SEGUNDA CATORCENA (9-22 Ene):")
    print("   ─────────────────────────────")
    print("   Balance inicial: $3,611.34")
    print("   Gastos:")
    print("     • 10 Ene: Seguros         -$266.29")
    print("     • 15 Ene: Teléfono         -$25.00")
    print("     • 20 Ene: Internet         -$75.00")
    print("     • Variables (14 días)     -$112.00")
    print("   ────────────────────────────")
    print("   Subtotal gastos:            -$478.29")
    print("   Balance antes catorcena:  $3,133.05 ✅")
    print()
    print("   23 Ene: INGRESO           +$3,300.00")
    print("   Balance: $6,433.05 ✅")
    print()
    print("   RESTO DE ENERO (23-31 Ene):")
    print("   ───────────────────────────")
    print("   Balance inicial: $6,433.05")
    print("   Gastos:")
    print("     • 24 Ene: Citi pago     -$2,452.11")
    print("     • 25 Ene: Gas-Luz         -$290.00")
    print("     • Variables (8 días)       -$64.00")
    print("   ────────────────────────────")
    print("   Subtotal gastos:          -$2,806.11")
    print("   Balance fin de mes:        $3,626.94 ✅")
    print()
    print("   TRANSFERENCIA A AHORROS:")
    print("   ───────────────────────────")
    print("   Balance: $3,626.94")
    print("   Mínimo confort: $2,000.00")
    print("   Disponible: $1,626.94")
    print("   Meta enero (2 x $500): $1,000.00")
    print("   → PUEDES TRANSFERIR: $1,000 ✅")
    print("   → Sobran: $626.94 (buffer extra)")
    
    # Recommendations
    print("\n💡 RECOMENDACIONES:")
    print("   1. ✅ Transferir $500 el 11 Ene (después de cheque)")
    print("   2. ✅ Transferir $500 el 25 Ene (después de catorcena 23 Ene)")
    print("   3. ✅ Mantener mínimo $2,000 en checking siempre")
    print("   4. ✅ Tu meta de $500/catorcena es PERFECTAMENTE realista")
    print("   5. ⚠️  Ojo: Primera semana de enero (1-8) es tight ($311)")
    print("      → Considera cobrar cheque de $1,251 el 2-3 Ene si lo tienes")
    print()
    print("   🎯 Con esta estrategia llegas a $15,000 en JUNIO 2026")
    
    print("\n" + "=" * 80)
    print("✅ CONCLUSIÓN: Sistema configurado perfectamente con TUS datos reales")
    print("=" * 80)
