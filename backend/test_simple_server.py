#!/usr/bin/env python3
"""
Simple test server to verify Flask is working
"""

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({'status': 'ok', 'message': 'Server is running'})

@app.route('/api/analytics/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Analytics service healthy'})

@app.route('/api/analytics/metrics/summary')
def metrics_summary():
    return jsonify({
        'status': 'success',
        'data': {
            'total_items': 0,
            'total_value': 0.0,
            'images_processed': 0,
            'total_queries': 0,
            'avg_items_per_query': 0.0,
            'avg_value_per_query': 0.0
        }
    })

if __name__ == '__main__':
    print("Starting simple test server...")
    app.run(host='0.0.0.0', port=8080, debug=True)
