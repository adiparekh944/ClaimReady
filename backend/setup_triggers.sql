-- Setup triggers for automatic analytics updates
-- Run this in your Supabase SQL Editor

-- Create the trigger function
CREATE OR REPLACE FUNCTION increment_global_metrics()
RETURNS TRIGGER AS $$
DECLARE
  job_price numeric(18,2);
  job_items bigint;
  job_has_video boolean;
BEGIN
  -- Extract values from job table
  job_price := COALESCE(NEW."total value", 0);
  job_items := COALESCE(NEW."numItems", 0);
  job_has_video := (NEW."videoAddress" IS NOT NULL AND NEW."videoAddress" != '');
  
  -- Update global_metrics
  UPDATE global_metrics SET
    total_price = total_price + job_price,
    total_images = total_images + (CASE WHEN job_has_video THEN 1 ELSE 0 END),
    total_items = total_items + job_items,
    total_queries = total_queries + 1,
    last_updated = now()
  WHERE id = 1;
  
  -- Update calculated averages
  UPDATE global_metrics SET
    avg_items_per_query = CASE WHEN total_queries > 0 THEN total_items::numeric / total_queries ELSE 0 END,
    avg_price_per_query = CASE WHEN total_queries > 0 THEN total_price / total_queries ELSE 0 END,
    avg_price_per_item = CASE WHEN total_items > 0 THEN total_price / total_items ELSE 0 END
  WHERE id = 1;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if it exists
DROP TRIGGER IF EXISTS trg_job_analytics ON job;

-- Create the trigger
CREATE TRIGGER trg_job_analytics
  AFTER INSERT ON job
  FOR EACH ROW
  EXECUTE FUNCTION increment_global_metrics();
