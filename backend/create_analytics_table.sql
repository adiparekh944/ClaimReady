-- Create the global_metrics table for ClaimReady Analytics
-- Run this in your Supabase SQL Editor

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

-- Insert the initial row
INSERT INTO global_metrics (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- Enable RLS (Row Level Security)
ALTER TABLE global_metrics ENABLE ROW LEVEL SECURITY;

-- Create policy for service role
CREATE POLICY "service can manage totals" ON global_metrics 
FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Grant permissions to authenticated users for reading
GRANT SELECT ON global_metrics TO authenticated;
GRANT SELECT ON global_metrics TO anon;
