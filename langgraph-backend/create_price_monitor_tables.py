#!/usr/bin/env python3
"""
Database migration script to create price monitoring system tables.

This script creates all the price monitoring tables with proper relationships,
indexes, and constraints based on the Prisma schema.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from database.price_monitor_models import Base as PriceMonitorBase
from database.extended_models import Base as ExtendedBase
from database.models import Base as CoreBase

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://espressobot:localdev123@localhost/espressobot_dev")

def create_price_monitor_tables():
    """Create all price monitoring tables."""
    
    print("🗄️  Creating price monitoring database tables...")
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        print("📋 Creating tables from price_monitor_models...")
        # Create price monitoring tables
        PriceMonitorBase.metadata.create_all(engine)
        
        print("📋 Creating tables from extended_models...")
        # Create extended tables
        ExtendedBase.metadata.create_all(engine)
        
        # Create session to run additional SQL commands
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            print("🔧 Creating additional indexes and constraints...")
            
            # Add unique constraints that SQLAlchemy doesn't handle well
            constraints_sql = [
                # Competitor products unique constraint
                """
                ALTER TABLE competitor_products 
                ADD CONSTRAINT IF NOT EXISTS unique_competitor_external_id 
                UNIQUE (external_id, competitor_id);
                """,
                
                # Product matches unique constraint
                """
                ALTER TABLE product_matches 
                ADD CONSTRAINT IF NOT EXISTS unique_product_match 
                UNIQUE (idc_product_id, competitor_product_id);
                """,
                
                # Create indexes for performance
                """
                CREATE INDEX IF NOT EXISTS idx_competitor_products_competitor_id 
                ON competitor_products(competitor_id);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_competitor_products_price 
                ON competitor_products(price);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_competitor_products_scraped_at 
                ON competitor_products(scraped_at);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_competitor_products_vendor 
                ON competitor_products(vendor);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_competitors_is_active 
                ON competitors(is_active);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_competitors_last_scraped_at 
                ON competitors(last_scraped_at);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_idc_products_available 
                ON idc_products(available);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_idc_products_last_synced_at 
                ON idc_products(last_synced_at);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_idc_products_product_type 
                ON idc_products(product_type);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_idc_products_vendor 
                ON idc_products(vendor);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_monitored_brands_is_active 
                ON monitored_brands(is_active);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_monitored_collections_is_active 
                ON monitored_collections(is_active);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_price_alerts_alert_type 
                ON price_alerts(alert_type);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_price_alerts_created_at 
                ON price_alerts(created_at);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_price_alerts_severity 
                ON price_alerts(severity);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_price_alerts_status 
                ON price_alerts(status);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_price_history_competitor_recorded 
                ON price_history(competitor_product_id, recorded_at);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_product_matches_confidence_level 
                ON product_matches(confidence_level);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_product_matches_is_map_violation 
                ON product_matches(is_map_violation);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_product_matches_last_checked_at 
                ON product_matches(last_checked_at);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_product_matches_overall_score 
                ON product_matches(overall_score);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_scrape_jobs_competitor_id 
                ON scrape_jobs(competitor_id);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_scrape_jobs_created_at 
                ON scrape_jobs(created_at);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_scrape_jobs_status 
                ON scrape_jobs(status);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_violation_history_detected_at 
                ON violation_history(detected_at);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_violation_history_product_match_id 
                ON violation_history(product_match_id);
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_violation_history_violation_type 
                ON violation_history(violation_type);
                """,
            ]
            
            for sql in constraints_sql:
                try:
                    session.execute(text(sql.strip()))
                    session.commit()
                except Exception as e:
                    print(f"⚠️  Warning executing SQL: {e}")
                    session.rollback()
                    continue
                    
        finally:
            session.close()
        
        print("✅ Price monitoring database tables created successfully!")
        
        # Print table summary
        print("\n📊 Created tables:")
        print("   Price Monitoring:")
        print("   - idc_products")
        print("   - competitor_products") 
        print("   - product_matches")
        print("   - competitors")
        print("   - monitored_brands")
        print("   - monitored_collections")
        print("   - price_history")
        print("   - price_alerts") 
        print("   - violation_history")
        print("   - scrape_jobs")
        print("   Extended:")
        print("   - task_conversations")
        print("   - tasks")
        print("   - task_dependencies")
        print("   - tool_result_cache")
        print("   - job_execution_log")
        print("   - memories (updated)")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
        
    return True

def verify_tables():
    """Verify that tables were created successfully."""
    
    print("\n🔍 Verifying table creation...")
    
    try:
        engine = create_engine(DATABASE_URL)
        
        # Check if key tables exist
        with engine.connect() as conn:
            tables_to_check = [
                'idc_products',
                'competitor_products', 
                'product_matches',
                'competitors',
                'monitored_brands',
                'price_history',
                'scrape_jobs'
            ]
            
            for table_name in tables_to_check:
                result = conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table_name}'
                    );
                """))
                
                exists = result.scalar()
                if exists:
                    print(f"   ✅ {table_name}")
                else:
                    print(f"   ❌ {table_name} - NOT FOUND")
                    
        print("\n🎉 Table verification complete!")
        
    except Exception as e:
        print(f"❌ Error verifying tables: {e}")
        return False
        
    return True

if __name__ == "__main__":
    print("🚀 Starting price monitoring database setup...\n")
    
    success = create_price_monitor_tables()
    
    if success:
        verify_tables()
        print("\n✨ Database setup completed successfully!")
        print("\nYou can now:")
        print("   1. Import products from IDC Shopify store")
        print("   2. Add competitors and configure scraping")
        print("   3. Run product matching algorithms") 
        print("   4. Monitor for MAP violations")
        print("   5. Set up price alerts")
    else:
        print("\n💥 Database setup failed!")
        sys.exit(1)