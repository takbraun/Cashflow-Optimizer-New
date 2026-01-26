"""
Migration script to add balance_is_closed field to Card table
"""

import sqlite3
import os
from datetime import datetime

def migrate_balance_field():
    db_path = 'instance/cashflow.db'
    
    if not os.path.exists(db_path):
        print("❌ No database found at instance/cashflow.db")
        return False
    
    print("🔄 Starting balance_is_closed migration...")
    print(f"   Database: {db_path}")
    
    # Backup first
    backup_path = f'instance/cashflow-backup-balance-{datetime.now().strftime("%Y%m%d-%H%M%S")}.db'
    import shutil
    shutil.copy(db_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if balance_is_closed column exists
        cursor.execute("PRAGMA table_info(card)")
        columns = {row[1]: row for row in cursor.fetchall()}
        
        if 'balance_is_closed' in columns:
            print("✅ balance_is_closed column already exists")
            return True
        
        print("\n📝 Adding balance_is_closed column to card table...")
        cursor.execute("""
            ALTER TABLE card 
            ADD COLUMN balance_is_closed BOOLEAN DEFAULT 0
        """)
        
        # Set balance_is_closed = True for cards with existing balance
        # Assume existing balances are closed statements (to be conservative)
        cursor.execute("""
            UPDATE card 
            SET balance_is_closed = 1 
            WHERE current_balance > 0
        """)
        
        updated_count = cursor.rowcount
        
        conn.commit()
        
        print("✅ balance_is_closed column added")
        print(f"   Updated {updated_count} cards with existing balances")
        
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
    print("🔄 Cash Flow Optimizer - Balance Field Migration")
    print("=" * 60)
    print()
    
    success = migrate_balance_field()
    
    print()
    print("=" * 60)
    
    if success:
        print("✅ Migration successful!")
        print("   You can now run: ./run.sh")
    else:
        print("❌ Migration failed")
        print("   Restore backup if needed:")
        print("   cp instance/cashflow-backup-balance-*.db instance/cashflow.db")
    
    print("=" * 60)
