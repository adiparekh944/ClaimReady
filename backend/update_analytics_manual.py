#!/usr/bin/env python3
"""
Manual analytics update script
Updates global_metrics based on job table data
"""

from supaDB import SupaDB

def update_analytics_manually():
    """Manually update analytics from job table data"""
    try:
        supabase = SupaDB()
        
        # Get all job data
        response = supabase.client.from_('job').select('*').execute()
        
        if not response.data:
            print("No job data found")
            return
        
        # Calculate totals
        total_price = 0
        total_items = 0
        total_images = 0
        total_queries = len(response.data)
        
        for job in response.data:
            total_price += float(job.get('total value', 0))
            total_items += int(job.get('numItems', 0))
            if job.get('videoAddress') and job.get('videoAddress') != '':
                total_images += 1
        
        # Calculate averages
        avg_items_per_query = total_items / total_queries if total_queries > 0 else 0
        avg_price_per_query = total_price / total_queries if total_queries > 0 else 0
        avg_price_per_item = total_price / total_items if total_items > 0 else 0
        
        # Update global_metrics
        update_data = {
            'total_price': total_price,
            'total_items': total_items,
            'total_images': total_images,
            'total_queries': total_queries,
            'avg_items_per_query': avg_items_per_query,
            'avg_price_per_query': avg_price_per_query,
            'avg_price_per_item': avg_price_per_item
        }
        
        response = supabase.client.from_('global_metrics').update(update_data).eq('id', 1).execute()
        
        if response.data:
            print("✅ Analytics updated successfully!")
            print(f"   Total Items: {total_items}")
            print(f"   Total Value: ${total_price:.2f}")
            print(f"   Total Images: {total_images}")
            print(f"   Total Queries: {total_queries}")
        else:
            print("❌ Failed to update analytics")
            
    except Exception as e:
        print(f"❌ Error updating analytics: {e}")

if __name__ == "__main__":
    update_analytics_manually()
