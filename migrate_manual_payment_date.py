"""
Migration script to add manual_payment_date field to Card table
"""

import sqlite3
import os
from datetime import datetime

def migrate_manual_payment_date():
    db_path = 'instance/cashflow.db'
    
    if not os.path.exists(db_path):
        print("❌ No database found at instance/cashflow.db")
        return False
    
    print("🔄 Starting manual_payment_date migration...")
    print(f"   Database: {db_path}")
    
    # Backup first
    backup_path = f'instance/cashflow-backup-manual-date-{datetime.now().strftime("%Y%m%d-%H%M%S")}.db'
    import shutil
    shutil.copy(db_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if manual_payment_date column exists
        cursor.execute("PRAGMA table_info(card)")
        columns = {row[1]: row for row in cursor.fetchall()}
        
        if 'manual_payment_date' in columns:
            print("✅ manual_payment_date column already exists")
            return True
        
        print("\n📝 Adding manual_payment_date column to card table...")
        cursor.execute("""
            ALTER TABLE card 
            ADD COLUMN manual_payment_date DATE NULL
        """)
        
        conn.commit()
        
        print("✅ manual_payment_date column added successfully")
        
        # Show current cards
        cursor.execute("SELECT name, current_balance, balance_is_closed FROM card")
        cards = cursor.fetchall()
        
        print(f"\n📊 Current cards:")
        for card in cards:
            status = "CLOSED" if card[2] else "OPEN"
            print(f"   {card[0]}: ${card[1]:.2f} ({status})")
        
        print(f"\n✅ Migration completed successfully!")
        print(f"   Backup available at: {backup_path}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        print(f"   Your original database is safe at: {backup_path}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == '__main__':
    print("=" * 60)
    print("🔄 Cash Flow Optimizer - Manual Payment Date Migration")
    print("=" * 60)
    print()
    
    success = migrate_manual_payment_date()
    
    print()
    print("=" * 60)
    
    if success:
        print("✅ Migration successful!")
        print("   You can now run: ./run.sh")
        print("\n   Now you can edit cards with closed balances")
        print("   and set custom payment dates manually.")
    else:
        print("❌ Migration failed")
        print("   Restore backup if needed:")
        print("   cp instance/cashflow-backup-manual-date-*.db instance/cashflow.db")
    
    print("=" * 60)
