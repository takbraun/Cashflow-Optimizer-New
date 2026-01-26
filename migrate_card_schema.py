"""
Migration script to update Card model schema
Adds payment_due_day and apr fields, removes old fields
"""

import sqlite3
import os
from datetime import datetime

def migrate_card_schema():
    db_path = 'instance/cashflow.db'
    
    if not os.path.exists(db_path):
        print("❌ No database found at instance/cashflow.db")
        return False
    
    print("🔄 Starting Card schema migration...")
    print(f"   Database: {db_path}")
    
    # Backup first
    backup_path = f'instance/cashflow-backup-{datetime.now().strftime("%Y%m%d-%H%M%S")}.db'
    import shutil
    shutil.copy(db_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current schema
        cursor.execute("PRAGMA table_info(card)")
        columns = {row[1]: row for row in cursor.fetchall()}
        
        print("\n📋 Current Card schema:")
        for col_name in columns:
            print(f"   - {col_name}")
        
        # Get existing cards data
        cursor.execute("SELECT id, name, closing_day, payment_days_after, credit_limit, current_balance FROM card")
        existing_cards = cursor.fetchall()
        
        print(f"\n💳 Found {len(existing_cards)} cards to migrate")
        
        # Create new card table with correct schema
        print("\n📝 Creating new card table...")
        cursor.execute("""
            CREATE TABLE card_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) NOT NULL UNIQUE,
                closing_day INTEGER NOT NULL,
                payment_due_day INTEGER NOT NULL,
                credit_limit FLOAT NOT NULL,
                current_balance FLOAT DEFAULT 0.0,
                apr FLOAT DEFAULT 0.0
            )
        """)
        
        # Migrate data - calculate payment_due_day from payment_days_after
        print("📊 Migrating card data...")
        for card in existing_cards:
            id, name, closing_day, payment_days_after, credit_limit, current_balance = card
            
            # Calculate payment_due_day
            # payment_days_after was days after closing
            # Convert to actual day of month
            # BofA: close 19, pay_after 5 = day 24
            # Amex: close 2, pay_after 25 = day 27
            # Citi: close 26, pay_after 28 = day 23 (next month)
            
            if name == 'BofA':
                payment_due_day = 24
            elif name == 'Amex':
                payment_due_day = 27
            elif name == 'Citi':
                payment_due_day = 23
            else:
                # Generic calculation
                payment_due_day = (closing_day + payment_days_after) % 31
                if payment_due_day == 0:
                    payment_due_day = 31
            
            cursor.execute("""
                INSERT INTO card_new (id, name, closing_day, payment_due_day, credit_limit, current_balance, apr)
                VALUES (?, ?, ?, ?, ?, ?, 0.0)
            """, (id, name, closing_day, payment_due_day, credit_limit, current_balance))
            
            print(f"   ✅ {name}: close day {closing_day} → payment day {payment_due_day}")
        
        # Drop old table and rename new one
        print("\n🔄 Replacing old table...")
        cursor.execute("DROP TABLE card")
        cursor.execute("ALTER TABLE card_new RENAME TO card")
        
        conn.commit()
        
        # Verify migration
        cursor.execute("SELECT id, name, closing_day, payment_due_day FROM card")
        migrated_cards = cursor.fetchall()
        
        print("\n✅ Migration completed successfully!")
        print("\n📊 Migrated cards:")
        for card in migrated_cards:
            print(f"   {card[1]}: Corte día {card[2]}, Pago día {card[3]}")
        
        print(f"\n🛡️  Backup available at: {backup_path}")
        
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
    print("🔄 Cash Flow Optimizer - Card Schema Migration")
    print("=" * 60)
    print()
    
    success = migrate_card_schema()
    
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
