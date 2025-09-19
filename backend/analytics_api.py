"""
Analytics API endpoints for ClaimReady
Provides global metrics data to the frontend
"""

from flask import Blueprint, jsonify
import logging
import os
import requests

# Configure logging
logger = logging.getLogger(__name__)

# Create analytics blueprint
analytics_bp = Blueprint('analytics', __name__)

def get_supabase_data(table, select_fields="*", filters=None):
    """Get data from Supabase using REST API"""
    try:
        url = f"https://hjomhelzgvdmjyhijyxr.supabase.co/rest/v1/{table}"
        headers = {
            'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imhqb21oZWx6Z3ZkbWp5aGlqeXhyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcwODU1MTMsImV4cCI6MjA2MjY2MTUxM30.D1pwL5D6uAv_e3hNkmb91ju2JsTDBf1xPk3OgJ-_71w',
            'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imhqb21oZWx6Z3ZkbWp5aGlqeXhyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcwODU1MTMsImV4cCI6MjA2MjY2MTUxM30.D1pwL5D6uAv_e3hNkmb91ju2JsTDBf1xPk3OgJ-_71w',
            'Content-Type': 'application/json'
        }
        
        params = {'select': select_fields}
        if filters:
            for key, value in filters.items():
                params[key] = value
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Supabase API error: {e}")
        return None

@analytics_bp.route('/api/analytics/metrics', methods=['GET'])
def get_global_metrics():
    """Get global analytics metrics"""
    try:
        # Get metrics from global_metrics table
        data = get_supabase_data('global_metrics', filters={'id': 'eq.1'})
        
        if not data:
            return jsonify({'error': 'Database connection failed'}), 500
        
        if not data:
            return jsonify({'error': 'No metrics found'}), 404
        
        result = data[0]
        
        # Map the result to a dictionary
        metrics = {
            'total_price': float(result.get('total_price', 0)),
            'total_images': int(result.get('total_images', 0)),
            'total_items': int(result.get('total_items', 0)),
            'total_queries': int(result.get('total_queries', 0)),
            'avg_items_per_query': float(result.get('avg_items_per_query', 0)),
            'avg_price_per_query': float(result.get('avg_price_per_query', 0)),
            'avg_price_per_item': float(result.get('avg_price_per_item', 0)),
            'last_updated': result.get('last_updated')
        }
        
        return jsonify({
            'status': 'success',
            'data': metrics
        })
        
    except Exception as e:
        logger.error(f"Error getting global metrics: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@analytics_bp.route('/api/analytics/metrics/summary', methods=['GET'])
def get_metrics_summary():
    """Get a simplified summary of metrics for dashboard display"""
    try:
        # Get just the essential metrics for the dashboard
        data = get_supabase_data('global_metrics', 
                                select_fields='total_items, total_price, total_images, total_queries, avg_items_per_query, avg_price_per_query',
                                filters={'id': 'eq.1'})
        
        if not data:
            return jsonify({'error': 'Database connection failed'}), 500
        
        if not data:
            return jsonify({'error': 'No metrics found'}), 404
        
        result = data[0]
        
        summary = {
            'total_items': int(result.get('total_items', 0)),
            'total_value': float(result.get('total_price', 0)),
            'images_processed': int(result.get('total_images', 0)),
            'total_queries': int(result.get('total_queries', 0)),
            'avg_items_per_query': float(result.get('avg_items_per_query', 0)),
            'avg_value_per_query': float(result.get('avg_price_per_query', 0))
        }
        
        return jsonify({
            'status': 'success',
            'data': summary
        })
        
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@analytics_bp.route('/api/analytics/health', methods=['GET'])
def analytics_health():
    """Health check for analytics service"""
    try:
        data = get_supabase_data('global_metrics', select_fields='id', filters={'id': 'eq.1'})
        
        if data is None:
            return jsonify({'status': 'error', 'message': 'Database connection failed'}), 500
        
        if data:
            return jsonify({'status': 'ok', 'message': 'Analytics service healthy'})
        else:
            return jsonify({'status': 'error', 'message': 'Metrics table not initialized'}), 500
            
    except Exception as e:
        logger.error(f"Analytics health check failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
