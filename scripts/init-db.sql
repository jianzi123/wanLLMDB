-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create TimescaleDB extension (if using TimescaleDB container)
-- This will be run in the metrics database separately
-- CREATE EXTENSION IF NOT EXISTS timescaledb;
