# ClaimReady Analytics System

A comprehensive analytics system that tracks global metrics across all queries sent to ClaimReady.

## 🎯 What It Tracks

The analytics system automatically tracks:

- **Total Items Detected** - Count of all items found across all queries
- **Total Value** - Sum of all estimated prices across all queries
- **Images Processed** - Total number of images analyzed
- **Total Queries** - Number of API calls made
- **Average Items per Query** - Mean items detected per query
- **Average Value per Query** - Mean estimated value per query
- **Average Price per Item** - Mean price per individual item

## 🏗️ Architecture

### Database Schema

- **`global_metrics`** - Single-row table storing live totals
- **Triggers** - Automatically update totals when `job_metrics` changes
- **Helper Functions** - SQL functions for easy data retrieval

### API Endpoints

- **`GET /api/analytics/metrics`** - Full metrics data with all fields
- **`GET /api/analytics/metrics/summary`** - Simplified data for dashboard
- **`GET /api/analytics/health`** - Health check for analytics service

### Frontend Components

- **`AnalyticsDashboard`** - React component for displaying metrics
- **`/analytics`** - Dedicated analytics page

## 🚀 Setup Instructions

### 1. Database Setup

```bash
# Navigate to backend directory
cd backend

# Set up the analytics schema
python setup_analytics.py
```

This will:

- Create the `global_metrics` table
- Set up triggers for automatic updates
- Create helper functions
- Test the setup

### 2. Backend Integration

The analytics blueprint is already integrated into your Flask app (`geminiserver.py`):

```python
from analytics_api import analytics_bp
app.register_blueprint(analytics_bp)
```

### 3. Frontend Integration

Add the analytics dashboard to any page:

```tsx
import AnalyticsDashboard from "@/components/AnalyticsDashboard";

// In your component
<AnalyticsDashboard />;
```

Or visit the dedicated analytics page at `/analytics`.

## 🧪 Testing

### Test the Analytics API

```bash
# Run the test suite
python test_analytics.py
```

### Test Individual Endpoints

```bash
# Health check
curl http://localhost:8080/api/analytics/health

# Metrics summary
curl http://localhost:8080/api/analytics/metrics/summary

# Full metrics
curl http://localhost:8080/api/analytics/metrics
```

## 📊 Usage Examples

### Frontend Integration

```tsx
// Fetch analytics data
const fetchAnalytics = async () => {
  const response = await fetch("/api/analytics/metrics/summary");
  const data = await response.json();

  if (data.status === "success") {
    const metrics = data.data;
    console.log("Total Items:", metrics.total_items);
    console.log("Total Value:", metrics.total_value);
    // ... use the data
  }
};
```

### Backend Integration

```python
# In your analysis functions, the metrics are automatically updated
# when you insert/update/delete records in job_metrics table

# The triggers handle everything automatically!
```

## 🔧 Configuration

### Environment Variables

Make sure your `DATABASE_URL` is set in your backend environment:

```bash
DATABASE_URL=postgresql://user:password@host:port/database
```

### Database Permissions

The analytics system uses Row Level Security (RLS) to ensure only the service role can modify the global metrics table.

## 📈 Real-time Updates

The analytics system updates in real-time:

- **INSERT** operations add to totals
- **UPDATE** operations apply deltas
- **DELETE** operations revert changes
- **Averages** are automatically recalculated

## 🎨 Frontend Dashboard

The analytics dashboard includes:

- **Live Metrics Cards** - Total items, value, and images
- **Additional Stats** - Queries, averages, and ratios
- **Auto-refresh** - Updates every 30 seconds
- **Error Handling** - Graceful error states and retry functionality
- **Responsive Design** - Works on all screen sizes

## 🔍 Troubleshooting

### Common Issues

1. **"Database connection failed"**

   - Check your `DATABASE_URL` environment variable
   - Ensure your database is running and accessible

2. **"No metrics found"**

   - Run the setup script: `python backend/setup_analytics.py`
   - Check that the `global_metrics` table exists

3. **"Analytics service unhealthy"**

   - Verify the analytics blueprint is registered in your Flask app
   - Check backend logs for errors

4. **Frontend not loading data**
   - Ensure your backend is running on the correct port
   - Check CORS configuration
   - Verify the API endpoints are accessible

### Debug Commands

```bash
# Check if analytics table exists
psql $DATABASE_URL -c "SELECT * FROM global_metrics;"

# Check if triggers are working
psql $DATABASE_URL -c "SELECT * FROM get_global_metrics();"

# Test API endpoints
curl -v http://localhost:8080/api/analytics/health
```

## 📝 API Reference

### GET /api/analytics/metrics

Returns full metrics data.

**Response:**

```json
{
  "status": "success",
  "data": {
    "total_price": 4645.0,
    "total_images": 0,
    "total_items": 21,
    "total_queries": 5,
    "avg_items_per_query": 4.2,
    "avg_price_per_query": 929.0,
    "avg_price_per_item": 221.19,
    "last_updated": "2024-01-15T10:30:00Z"
  }
}
```

### GET /api/analytics/metrics/summary

Returns simplified metrics for dashboard display.

**Response:**

```json
{
  "status": "success",
  "data": {
    "total_items": 21,
    "total_value": 4645.0,
    "images_processed": 0,
    "total_queries": 5,
    "avg_items_per_query": 4.2,
    "avg_value_per_query": 929.0
  }
}
```

### GET /api/analytics/health

Health check endpoint.

**Response:**

```json
{
  "status": "ok",
  "message": "Analytics service healthy"
}
```

## 🎉 Success!

Your analytics system is now tracking all ClaimReady queries automatically. The metrics will update in real-time as users submit images for analysis, giving you valuable insights into your platform's usage and performance.
