-- Enhanced Global Metrics Schema for ClaimReady Analytics
-- This tracks all queries sent to the ClaimReady backend

-- 1) Enhanced global metrics table
create table if not exists global_metrics (
  id int primary key check (id = 1),
  total_price numeric(18,2) not null default 0,
  total_images bigint not null default 0,
  total_items bigint not null default 0,
  total_queries bigint not null default 0,
  -- Additional metrics for better analytics
  avg_items_per_query numeric(10,2) not null default 0,
  avg_price_per_query numeric(18,2) not null default 0,
  avg_price_per_item numeric(18,2) not null default 0,
  -- Timestamps for tracking
  last_updated timestamp with time zone not null default now(),
  created_at timestamp with time zone not null default now()
);

-- Initialize the single row
insert into global_metrics (id) values (1) on conflict (id) do nothing;

-- 2) Enhanced trigger function with calculated averages
-- Updated to work with your existing 'job' table structure
create or replace function increment_global_metrics()
returns trigger language plpgsql as $$
declare
  new_total_price numeric(18,2);
  new_total_images bigint;
  new_total_items bigint;
  new_total_queries bigint;
  job_price numeric(18,2);
  job_items bigint;
  job_has_video boolean;
begin
  -- Extract values from job table (using your actual column names)
  job_price := COALESCE(new."total value", 0);
  job_items := COALESCE(new."numItems", 0);
  job_has_video := (new."videoAddress" IS NOT NULL AND new."videoAddress" != '');
  
  -- INSERT
  if (tg_op = 'INSERT') then
    update global_metrics
    set 
      total_price = total_price + job_price,
      total_images = total_images + (case when job_has_video then 1 else 0 end),
      total_items = total_items + job_items,
      total_queries = total_queries + 1,
      last_updated = now()
    returning total_price, total_images, total_items, total_queries
    into new_total_price, new_total_images, new_total_items, new_total_queries;
    
    -- Update calculated averages
    update global_metrics
    set 
      avg_items_per_query = case when new_total_queries > 0 then new_total_items::numeric / new_total_queries else 0 end,
      avg_price_per_query = case when new_total_queries > 0 then new_total_price / new_total_queries else 0 end,
      avg_price_per_item = case when new_total_items > 0 then new_total_price / new_total_items else 0 end;
    
    return new;
  end if;

  -- UPDATE (apply deltas)
  if (tg_op = 'UPDATE') then
    -- Calculate deltas
    job_price := COALESCE(new."total value", 0) - COALESCE(old."total value", 0);
    job_items := COALESCE(new."numItems", 0) - COALESCE(old."numItems", 0);
    job_has_video := (new."videoAddress" IS NOT NULL AND new."videoAddress" != '') AND 
                     (old."videoAddress" IS NULL OR old."videoAddress" = '');
    
    update global_metrics
    set 
      total_price = total_price + job_price,
      total_images = total_images + (case when job_has_video then 1 else 0 end),
      total_items = total_items + job_items,
      last_updated = now()
    returning total_price, total_images, total_items, total_queries
    into new_total_price, new_total_images, new_total_items, new_total_queries;
    
    -- Update calculated averages
    update global_metrics
    set 
      avg_items_per_query = case when new_total_queries > 0 then new_total_items::numeric / new_total_queries else 0 end,
      avg_price_per_query = case when new_total_queries > 0 then new_total_price / new_total_queries else 0 end,
      avg_price_per_item = case when new_total_items > 0 then new_total_price / new_total_items else 0 end;
    
    return new;
  end if;

  -- DELETE (revert)
  if (tg_op = 'DELETE') then
    job_price := COALESCE(old."total value", 0);
    job_items := COALESCE(old."numItems", 0);
    job_has_video := (old."videoAddress" IS NOT NULL AND old."videoAddress" != '');
    
    update global_metrics
    set 
      total_price = total_price - job_price,
      total_images = total_images - (case when job_has_video then 1 else 0 end),
      total_items = total_items - job_items,
      total_queries = total_queries - 1,
      last_updated = now()
    returning total_price, total_images, total_items, total_queries
    into new_total_price, new_total_images, new_total_items, new_total_queries;
    
    -- Update calculated averages
    update global_metrics
    set 
      avg_items_per_query = case when new_total_queries > 0 then new_total_items::numeric / new_total_queries else 0 end,
      avg_price_per_query = case when new_total_queries > 0 then new_total_price / new_total_queries else 0 end,
      avg_price_per_item = case when new_total_items > 0 then new_total_price / new_total_items else 0 end;
    
    return old;
  end if;

  return null;
end $$;

-- 3) Attach triggers to your existing job table
drop trigger if exists trg_job_totals_ins on job;
drop trigger if exists trg_job_totals_upd on job;
drop trigger if exists trg_job_totals_del on job;

create trigger trg_job_totals_ins
after insert on job
for each row execute function increment_global_metrics();

create trigger trg_job_totals_upd
after update on job
for each row execute function increment_global_metrics();

create trigger trg_job_totals_del
after delete on job
for each row execute function increment_global_metrics();

-- 4) Security: Only service role can manage totals
alter table global_metrics enable row level security;
create policy "service can manage totals"
on global_metrics for all to service_role using (true) with check (true);

-- 5) Helper function to get current metrics (for API endpoints)
create or replace function get_global_metrics()
returns table (
  total_price numeric(18,2),
  total_images bigint,
  total_items bigint,
  total_queries bigint,
  avg_items_per_query numeric(10,2),
  avg_price_per_query numeric(18,2),
  avg_price_per_item numeric(18,2),
  last_updated timestamp with time zone
) language sql security definer as $$
  select 
    total_price,
    total_images,
    total_items,
    total_queries,
    avg_items_per_query,
    avg_price_per_query,
    avg_price_per_item,
    last_updated
  from global_metrics 
  where id = 1;
$$;

-- 6) Grant permissions
grant execute on function get_global_metrics() to anon, authenticated;
grant select on global_metrics to anon, authenticated;
