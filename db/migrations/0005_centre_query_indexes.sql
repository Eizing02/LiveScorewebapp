CREATE INDEX fixtures_kickoff_all ON fixtures(kickoff_utc,id);
CREATE INDEX analysis_snapshot_lookup ON analysis_snapshots(fixture_id,model_version,generated_at,id);
