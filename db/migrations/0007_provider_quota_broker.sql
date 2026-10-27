ALTER TABLE quota_windows ADD COLUMN per_minute INTEGER NOT NULL DEFAULT 5;
ALTER TABLE api_usage ADD COLUMN settled_at INTEGER;
ALTER TABLE api_usage ADD COLUMN settlement_token TEXT;
CREATE INDEX provider_usage_ticket ON api_usage(id,window_id,settled_at);
