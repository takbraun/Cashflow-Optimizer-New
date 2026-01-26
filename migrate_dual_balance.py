#!/usr/bin/env python3
"""
Migration: Add closed_balance and open_balance fields to card table
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
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(card)")
    columns = [row[1] for row in cursor.fetchall()]
    
    changes_made = False
    
    if 'closed_balance' not in columns:
        # Add closed_balance column
        cursor.execute("""
            ALTER TABLE card 
            ADD COLUMN closed_balance FLOAT DEFAULT 0.0
        """)
        print("✅ Added closed_balance column to card")
        changes_made = True
    
    if 'open_balance' not in columns:
        # Add open_balance column
        cursor.execute("""
            ALTER TABLE card 
            ADD COLUMN open_balance FLOAT DEFAULT 0.0
        """)
        print("✅ Added open_balance column to card")
        changes_made = True
    
    if changes_made:
        # Migrate existing data
        cursor.execute("""
            UPDATE card 
            SET closed_balance = CASE 
                WHEN balance_is_closed = 1 THEN current_balance
                ELSE 0.0
            END,
            open_balance = CASE 
                WHEN balance_is_closed = 0 THEN current_balance
                ELSE 0.0
            END
            WHERE current_balance > 0
        """)
        
        rows_updated = cursor.rowcount
        print(f"✅ Migrated {rows_updated} cards with existing balances")
        print("\nMigration details:")
        
        # Show migrated data
        cursor.execute("""
            SELECT name, current_balance, balance_is_closed, closed_balance, open_balance 
            FROM card 
            WHERE current_balance > 0
        """)
        
        for row in cursor.fetchall():
            name, current, is_closed, closed, open_bal = row
            status = "CLOSED" if is_closed else "OPEN"
            print(f"  {name}: ${current:.2f} ({status}) → closed=${closed:.2f}, open=${open_bal:.2f}")
    else:
        print("ℹ️  Columns already exist, no migration needed")
    
    conn.commit()
    print("\n✅ Migration completed successfully!")
    
except Exception as e:
    conn.rollback()
    print(f"❌ Migration failed: {e}")
    print(f"💡 Database backup available at: {backup_file}")
    raise

finally:
    conn.close()
