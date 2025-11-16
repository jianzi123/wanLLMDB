-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create metrics table
CREATE TABLE IF NOT EXISTS metrics (
    time TIMESTAMPTZ NOT NULL,
    run_id UUID NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    step INTEGER,
    value DOUBLE PRECISION NOT NULL,
    metadata JSONB
);

-- Convert to hypertable
SELECT create_hypertable('metrics', 'time', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_metrics_run_id_time ON metrics (run_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_name_time ON metrics (run_id, metric_name, time DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_step ON metrics (run_id, step);

-- Create system metrics table
CREATE TABLE IF NOT EXISTS system_metrics (
    time TIMESTAMPTZ NOT NULL,
    run_id UUID NOT NULL,
    cpu_percent DOUBLE PRECISION,
    memory_percent DOUBLE PRECISION,
    memory_used_mb DOUBLE PRECISION,
    gpu_utilization JSONB,
    disk_io JSONB,
    network_io JSONB
);

-- Convert to hypertable
SELECT create_hypertable('system_metrics', 'time', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_system_metrics_run_id_time ON system_metrics (run_id, time DESC);

-- Create continuous aggregates for hourly metrics
CREATE MATERIALIZED VIEW IF NOT EXISTS metrics_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    run_id,
    metric_name,
    AVG(value) as avg_value,
    MIN(value) as min_value,
    MAX(value) as max_value,
    STDDEV(value) as stddev_value,
    COUNT(*) as count
FROM metrics
GROUP BY bucket, run_id, metric_name
WITH NO DATA;

-- Refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('metrics_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Data retention policy (keep metrics for 90 days)
SELECT add_retention_policy('metrics', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('system_metrics', INTERVAL '30 days', if_not_exists => TRUE);

-- Create function to get latest metric value
CREATE OR REPLACE FUNCTION get_latest_metric_value(
    p_run_id UUID,
    p_metric_name VARCHAR
)
RETURNS DOUBLE PRECISION AS $$
DECLARE
    latest_value DOUBLE PRECISION;
BEGIN
    SELECT value INTO latest_value
    FROM metrics
    WHERE run_id = p_run_id
      AND metric_name = p_metric_name
    ORDER BY time DESC
    LIMIT 1;

    RETURN latest_value;
END;
$$ LANGUAGE plpgsql;

-- Create function to get metric statistics
CREATE OR REPLACE FUNCTION get_metric_stats(
    p_run_id UUID,
    p_metric_name VARCHAR
)
RETURNS TABLE (
    min_value DOUBLE PRECISION,
    max_value DOUBLE PRECISION,
    avg_value DOUBLE PRECISION,
    latest_value DOUBLE PRECISION,
    count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        MIN(m.value),
        MAX(m.value),
        AVG(m.value),
        (SELECT value FROM metrics WHERE run_id = p_run_id AND metric_name = p_metric_name ORDER BY time DESC LIMIT 1),
        COUNT(*)
    FROM metrics m
    WHERE m.run_id = p_run_id
      AND m.metric_name = p_metric_name;
END;
$$ LANGUAGE plpgsql;
