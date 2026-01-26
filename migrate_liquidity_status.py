#!/usr/bin/env python3
"""
Migration: Add liquidity_status field to purchase_recommendation table
"""
import sqlite3
import shutil
from datetime import datetime

# Backup database first
backup_file = f"instance/cashflow_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
shutil.copy2('instance/cashflow.db', backup_file)
print(f"✅ Backup created: {backup_file}")

# Connect to database
conn = sqlite3.connect('instance/cashflow.db')
cursor = conn.cursor()

try:
    # Check if column already exists
    cursor.execute("PRAGMA table_info(purchase_recommendation)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'liquidity_status' not in columns:
        # Add liquidity_status column
        cursor.execute("""
            ALTER TABLE purchase_recommendation 
            ADD COLUMN liquidity_status VARCHAR(20) DEFAULT 'safe'
        """)
        print("✅ Added liquidity_status column to purchase_recommendation")
        
        # Update existing records based on can_afford_now
        cursor.execute("""
            UPDATE purchase_recommendation 
            SET liquidity_status = CASE 
                WHEN can_afford_now = 1 THEN 'safe'
                ELSE 'critical'
            END
        """)
        print("✅ Updated existing records with liquidity status")
        
    else:
        print("ℹ️  liquidity_status column already exists")
    
    conn.commit()
    print("✅ Migration completed successfully!")
    
except Exception as e:
    conn.rollback()
    print(f"❌ Migration failed: {e}")
    print(f"💡 Database backup available at: {backup_file}")
    raise

finally:
    conn.close()
