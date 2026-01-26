#!/usr/bin/env python3
"""
Migration: Add ExpenseCategory table and default categories
"""
from app import app, db, ExpenseCategory

def migrate():
    with app.app_context():
        print("Creating ExpenseCategory table...")
        
        # Create table
        db.create_all()
        
        # Default categories with icons
        default_categories = [
            {'name': 'Comida/Restaurantes', 'icon': '🍔'},
            {'name': 'Gasolina', 'icon': '⛽'},
            {'name': 'Shopping personal', 'icon': '🛍️'},
            {'name': 'Entretenimiento', 'icon': '🎬'},
            {'name': 'Transporte', 'icon': '🚗'},
            {'name': 'Salud', 'icon': '🏥'},
            {'name': 'Educación', 'icon': '📚'},
            {'name': 'Hogar', 'icon': '🏠'},
            {'name': 'Otros', 'icon': '📌'}
        ]
        
        print("\nAdding default categories:")
        for cat_data in default_categories:
            existing = ExpenseCategory.query.filter_by(name=cat_data['name']).first()
            if not existing:
                category = ExpenseCategory(**cat_data)
                db.session.add(category)
                print(f"  ✅ {cat_data['icon']} {cat_data['name']}")
            else:
                print(f"  ⏭️  {cat_data['name']} (already exists)")
        
        db.session.commit()
        print("\n✅ Migration completed successfully!")

if __name__ == '__main__':
    migrate()
