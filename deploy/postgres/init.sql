-- PostgreSQL initialization script
-- Runs once when the data volume is first created

-- Create the application database (if not using POSTGRES_DB env var)
-- CREATE DATABASE automated_software;

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- trigram similarity for text search
CREATE EXTENSION IF NOT EXISTS btree_gin;    -- GIN indexes for composite queries
