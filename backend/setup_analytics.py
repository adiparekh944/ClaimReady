#!/usr/bin/env python3
"""
Setup script for ClaimReady Analytics
Creates the global_metrics table and triggers
"""

import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get database connection using DATABASE_URL from environment"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def setup_analytics_schema():
    """Set up the analytics schema"""
    conn = get_db_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Read and execute the schema file
        with open('analytics_schema.sql', 'r') as f:
            schema_sql = f.read()
        
        # Split by semicolon and execute each statement
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        for statement in statements:
            if statement:
                print(f"Executing: {statement[:50]}...")
                cursor.execute(statement)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Analytics schema setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error setting up analytics schema: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def test_analytics():
    """Test the analytics setup"""
    conn = get_db_connection()
    if not conn:
        print("❌ Failed to connect to database for testing")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Test the global_metrics table
        cursor.execute("SELECT * FROM global_metrics WHERE id = 1;")
        result = cursor.fetchone()
        
        if result:
            print("✅ Global metrics table is working!")
            print(f"   Total Items: {result[2]}")
            print(f"   Total Price: ${result[1]}")
            print(f"   Total Images: {result[3]}")
            print(f"   Total Queries: {result[4]}")
        else:
            print("❌ Global metrics table not found or empty")
            return False
        
        # Test the helper function
        cursor.execute("SELECT * FROM get_global_metrics();")
        result = cursor.fetchone()
        
        if result:
            print("✅ Analytics API function is working!")
        else:
            print("❌ Analytics API function not working")
            return False
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error testing analytics: {e}")
        if conn:
            conn.close()
        return False

if __name__ == "__main__":
    print("🚀 Setting up ClaimReady Analytics...")
    
    if setup_analytics_schema():
        print("\n🧪 Testing analytics setup...")
        if test_analytics():
            print("\n🎉 Analytics setup completed successfully!")
            print("\n📊 Available API endpoints:")
            print("   GET /api/analytics/metrics - Full metrics data")
            print("   GET /api/analytics/metrics/summary - Dashboard summary")
            print("   GET /api/analytics/health - Health check")
        else:
            print("\n❌ Analytics setup failed testing")
    else:
        print("\n❌ Analytics setup failed")
