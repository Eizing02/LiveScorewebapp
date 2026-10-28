CREATE TABLE program_sync_runs(id TEXT PRIMARY KEY,started_at TEXT NOT NULL,completed_at TEXT,status TEXT NOT NULL CHECK(status IN ('running','complete','failed')),business_date TEXT NOT NULL,source_dates TEXT NOT NULL,fixtures_count INTEGER NOT NULL DEFAULT 0,quarantined_count INTEGER NOT NULL DEFAULT 0,error_code TEXT);
CREATE INDEX program_sync_recent ON program_sync_runs(started_at DESC);
CREATE TABLE program_fixture_fingerprints(fixture_id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,verified_at TEXT NOT NULL);
