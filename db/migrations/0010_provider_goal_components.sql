CREATE TABLE provider_goal_components(id TEXT PRIMARY KEY,created_at TEXT NOT NULL,payload TEXT NOT NULL,checksum TEXT NOT NULL);
CREATE TRIGGER provider_goal_component_no_update BEFORE UPDATE ON provider_goal_components BEGIN SELECT RAISE(ABORT,'goal_component_immutable'); END;
CREATE TRIGGER provider_goal_component_no_delete BEFORE DELETE ON provider_goal_components BEGIN SELECT RAISE(ABORT,'goal_component_immutable'); END;
