"""
Migration script to update existing database with new fields
Run this BEFORE using the new version if you have existing data
"""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    db_path = 'instance/cashflow.db'
    
    if not os.path.exists(db_path):
        print("❌ No database found at instance/cashflow.db")
        print("   If you have an existing database, make sure you're in the cashflow-optimizer directory")
        return False
    
    print("🔄 Starting database migration...")
    print(f"   Database: {db_path}")
    
    # Backup first
    backup_path = f'instance/cashflow-backup-{datetime.now().strftime("%Y%m%d-%H%M%S")}.db'
    import shutil
    shutil.copy(db_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if card_id column exists in variable_expense_log
        cursor.execute("PRAGMA table_info(variable_expense_log)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'card_id' not in columns:
            print("📝 Adding card_id column to variable_expense_log...")
            cursor.execute("""
                ALTER TABLE variable_expense_log 
                ADD COLUMN card_id INTEGER
            """)
            print("✅ card_id column added")
        else:
            print("✅ card_id column already exists")
        
        # Check if CardPayment table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='card_payment'")
        if not cursor.fetchone():
            print("📝 Creating card_payment table...")
            cursor.execute("""
                CREATE TABLE card_payment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    payment_date TIMESTAMP NOT NULL,
                    notes VARCHAR(200),
                    FOREIGN KEY (card_id) REFERENCES card(id)
                )
            """)
            print("✅ card_payment table created")
        else:
            print("✅ card_payment table already exists")
        
        # Verify expense_date exists and is properly set
        cursor.execute("SELECT COUNT(*) FROM variable_expense_log WHERE expense_date IS NULL")
        null_count = cursor.fetchone()[0]
        
        if null_count > 0:
            print(f"📝 Fixing {null_count} records with NULL expense_date...")
            cursor.execute("""
                UPDATE variable_expense_log 
                SET expense_date = datetime('now')
                WHERE expense_date IS NULL
            """)
            print("✅ NULL expense_date values fixed")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        print(f"   Your data is safe and the database is updated")
        print(f"   Backup available at: {backup_path}")
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM variable_expense_log")
        var_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM expense_payment")
        fixed_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM card_payment")
        card_payment_count = cursor.fetchone()[0]
        
        print(f"\n📊 Current data:")
        print(f"   Variable expenses: {var_count}")
        print(f"   Fixed expenses paid: {fixed_count}")
        print(f"   Card payments: {card_payment_count}")
        
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
    print("🔄 Cash Flow Optimizer - Database Migration")
    print("=" * 60)
    print()
    
    success = migrate_database()
    
    print()
    print("=" * 60)
    
    if success:
        print("✅ Migration successful!")
        print("   You can now run: ./run.sh")
    else:
        print("❌ Migration failed")
        print("   Restore backup if needed:")
        print("   cp instance/cashflow-backup-*.db instance/cashflow.db")
    
    print("=" * 60)
