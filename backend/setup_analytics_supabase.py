#!/usr/bin/env python3
"""
Setup script for ClaimReady Analytics with Supabase
Creates the global_metrics table and initializes it
"""

from supaDB import SupaDB
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_analytics_supabase():
    """Set up the analytics schema using Supabase"""
    try:
        supabase = SupaDB()
        print("✅ Connected to Supabase")
        
        # Create the global_metrics table using raw SQL
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS global_metrics (
            id int PRIMARY KEY CHECK (id = 1),
            total_price numeric(18,2) NOT NULL DEFAULT 0,
            total_images bigint NOT NULL DEFAULT 0,
            total_items bigint NOT NULL DEFAULT 0,
            total_queries bigint NOT NULL DEFAULT 0,
            avg_items_per_query numeric(10,2) NOT NULL DEFAULT 0,
            avg_price_per_query numeric(18,2) NOT NULL DEFAULT 0,
            avg_price_per_item numeric(18,2) NOT NULL DEFAULT 0,
            last_updated timestamp with time zone NOT NULL DEFAULT now(),
            created_at timestamp with time zone NOT NULL DEFAULT now()
        );
        """
        
        print("📊 Creating global_metrics table...")
        response = supabase.client.rpc('exec_sql', {'sql': create_table_sql}).execute()
        print("✅ Table created successfully")
        
        # Insert initial row
        print("🔢 Initializing metrics row...")
        response = supabase.client.from_('global_metrics').upsert({
            'id': 1,
            'total_price': 0,
            'total_images': 0,
            'total_items': 0,
            'total_queries': 0,
            'avg_items_per_query': 0,
            'avg_price_per_query': 0,
            'avg_price_per_item': 0
        }).execute()
        
        if response.data:
            print("✅ Metrics initialized successfully!")
            return True
        else:
            print("❌ Failed to initialize metrics")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up analytics: {e}")
        logger.error(f"Setup error: {e}")
        return False

def test_analytics_supabase():
    """Test the analytics setup"""
    try:
        supabase = SupaDB()
        print("🧪 Testing analytics setup...")
        
        # Test reading from global_metrics
        response = supabase.client.from_('global_metrics').select('*').eq('id', 1).execute()
        
        if response.data:
            result = response.data[0]
            print("✅ Analytics table is working!")
            print(f"   Total Items: {result.get('total_items', 0)}")
            print(f"   Total Price: ${result.get('total_price', 0)}")
            print(f"   Total Images: {result.get('total_images', 0)}")
            print(f"   Total Queries: {result.get('total_queries', 0)}")
            return True
        else:
            print("❌ Analytics table not found or empty")
            return False
            
    except Exception as e:
        print(f"❌ Error testing analytics: {e}")
        logger.error(f"Test error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Setting up ClaimReady Analytics with Supabase...")
    
    if setup_analytics_supabase():
        print("\n🧪 Testing analytics setup...")
        if test_analytics_supabase():
            print("\n🎉 Analytics setup completed successfully!")
            print("\n📊 Available API endpoints:")
            print("   GET /api/analytics/metrics - Full metrics data")
            print("   GET /api/analytics/metrics/summary - Dashboard summary")
            print("   GET /api/analytics/health - Health check")
            print("\n💡 Note: Triggers need to be set up manually in Supabase dashboard")
            print("   The analytics will work, but won't auto-update until triggers are added")
        else:
            print("\n❌ Analytics setup failed testing")
    else:
        print("\n❌ Analytics setup failed")
