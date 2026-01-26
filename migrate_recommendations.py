"""
Migration script to add PurchaseRecommendation and DeferredPaymentSchedule tables
"""

import sqlite3
import os
from datetime import datetime

def migrate_recommendation_tables():
    db_path = 'instance/cashflow.db'
    
    if not os.path.exists(db_path):
        print("❌ No database found at instance/cashflow.db")
        return False
    
    print("🔄 Starting recommendation tables migration...")
    print(f"   Database: {db_path}")
    
    # Backup first
    backup_path = f'instance/cashflow-backup-recommendations-{datetime.now().strftime("%Y%m%d-%H%M%S")}.db'
    import shutil
    shutil.copy(db_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='purchase_recommendation'")
        if cursor.fetchone():
            print("✅ purchase_recommendation table already exists")
        else:
            print("\n📝 Creating purchase_recommendation table...")
            cursor.execute("""
                CREATE TABLE purchase_recommendation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount FLOAT NOT NULL,
                    purchase_date DATE NOT NULL,
                    is_deferred BOOLEAN DEFAULT 0,
                    num_payments INTEGER,
                    payment_frequency VARCHAR(20),
                    payment_amount FLOAT,
                    recommended_card_id INTEGER NOT NULL,
                    can_afford_now BOOLEAN DEFAULT 1,
                    suggested_wait_date DATE,
                    status VARCHAR(20) DEFAULT 'pending',
                    description VARCHAR(200),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    executed_at DATETIME,
                    FOREIGN KEY (recommended_card_id) REFERENCES card (id)
                )
            """)
            print("✅ purchase_recommendation table created")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='deferred_payment_schedule'")
        if cursor.fetchone():
            print("✅ deferred_payment_schedule table already exists")
        else:
            print("\n📝 Creating deferred_payment_schedule table...")
            cursor.execute("""
                CREATE TABLE deferred_payment_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recommendation_id INTEGER NOT NULL,
                    payment_number INTEGER NOT NULL,
                    payment_amount FLOAT NOT NULL,
                    expected_date DATE NOT NULL,
                    card_statement_close_date DATE NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    FOREIGN KEY (recommendation_id) REFERENCES purchase_recommendation (id)
                )
            """)
            print("✅ deferred_payment_schedule table created")
        
        conn.commit()
        
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
    print("🔄 Cash Flow Optimizer - Recommendation Tables Migration")
    print("=" * 60)
    print()
    
    success = migrate_recommendation_tables()
    
    print()
    print("=" * 60)
    
    if success:
        print("✅ Migration successful!")
        print("   New tables added:")
        print("   - purchase_recommendation")
        print("   - deferred_payment_schedule")
        print("\n   You can now run: ./run.sh")
    else:
        print("❌ Migration failed")
        print("   Restore backup if needed:")
        print("   cp instance/cashflow-backup-recommendations-*.db instance/cashflow.db")
    
    print("=" * 60)
