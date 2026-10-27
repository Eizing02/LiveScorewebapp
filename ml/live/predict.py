"""Fresh whole-date features with frozen v3 weights, without changing old evidence."""
from zoneinfo import ZoneInfo

from ml.live.normalize import LEAGUES, moment, sha, stamp
from ml.precision_predict import PrecisionEngine, list_records
from ml.precision.goals import DixonColes


class LivePrecisionEngine(PrecisionEngine):
    def __init__(self, matches, generated_at, dataset_version, version=None, runtime_version=None, component_directory=None):
        import hashlib
        from pathlib import Path
        self.runtime_version = runtime_version or "live-engine-"+hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]
        self.component_directory = component_directory
        self.generated_at = stamp(generated_at)
        self.live_dataset_version = dataset_version
        allowed = [r for r in matches if not r.get("available_at") or moment(r["available_at"]) <= moment(generated_at)]
        super().__init__(version=version, matches=allowed)
        if component_directory is not None:
            from ml.live.ledger import read_kind
            for item in sorted(read_kind(component_directory, "goal-components"), key=lambda c: c.get("created_at", "")):
                if not item.get("created_at") or moment(item["created_at"]) > moment(generated_at):
                    continue
                self.goal_models[item["league"]+":"+item["model"]] = DixonColes.from_dict(item["weights"])
        self.information_cutoff = None

    def snapshot(self, fixture, information_cutoff_exclusive=None):
        cutoff = information_cutoff_exclusive or self.information_cutoff
        if cutoff is None:
            raise ValueError("explicit_feature_information_cutoff_required")
        return super().snapshot(fixture, cutoff)

    def predict_live(self, fixture):
        generated, kickoff = moment(self.generated_at), moment(fixture["kickoff_utc"])
        if generated >= kickoff or fixture["status"] != "scheduled":
            raise ValueError("no_prediction_after_kickoff_or_started_fixture")
        if fixture["mapping_status"] != "reviewed" or fixture["quarantine_reasons"]:
            raise ValueError("fixture_identity_or_quality_pending")
        timezone_name = LEAGUES[fixture["provider_league_id"]][4]
        self.information_cutoff = min(fixture["date"], generated.astimezone(ZoneInfo(timezone_name)).date().isoformat())
        if self.information_cutoff < self.meta["training_cutoff_exclusive"]:
            raise ValueError("weights_not_available_at_feature_cutoff")
        def bucket(day):
            return (day[:4], (int(day[5:7])-1)//2)
        components = {}
        for name in ["dc180-r4", "dc365-r4"]:
            key = fixture["league"]+":"+name
            goal = self.goal_models[key]
            if bucket(goal.cutoff) != bucket(self.information_cutoff):
                history = [r for r in self.matches if r["league"] == fixture["league"] and r["date"] < self.information_cutoff]
                if len(history) < 60:
                    raise ValueError("insufficient_history_for_goal_component_refit")
                goal = DixonColes(half_life_days=goal.half_life_days, ridge=goal.ridge).fit(history, self.information_cutoff)
                self.goal_models[key] = goal
                from ml.live.ledger import write_once
                if self.component_directory is not None:
                    write_once(self.component_directory, "goal-components", {"league": fixture["league"], "model": name, "weights": goal.to_dict(), "dataset_version": self.live_dataset_version, "created_at": self.generated_at})
            components[name] = {"sha256": sha(goal.to_dict()), "training_cutoff": goal.cutoff, "training_last_date": goal.training_last_date}
        snapshot = super().predict({**fixture, "id": fixture["fixture_id"]}, self.generated_at)
        row, _ = self.snapshot(fixture)
        snapshot.update({"mode": "private_research", "dataset_version": self.live_dataset_version, "weights_training_cutoff": self.meta["training_cutoff_exclusive"], "feature_information_cutoff_exclusive": self.information_cutoff, "feature_time_grain": "strictly_previous_competition_dates", "occurrence_id": fixture["occurrence_id"], "observation_id": fixture["observation_id"], "mapping_version": fixture["mapping_version"], "live_approved": False, "enrichment_used_in_weights": False, "last_result_dates": [records[-1]["date"] if records else "" for records in [list_records(self.matches, fixture, "home", self.information_cutoff), list_records(self.matches, fixture, "away", self.information_cutoff)]]})
        snapshot["model_version"] += ":goals-"+sha(components)[:12]
        snapshot["runtime_version"] = self.runtime_version
        snapshot["snapshot_id"] = "live-"+sha([fixture["fixture_id"], fixture["occurrence_id"], self.generated_at, snapshot["model_version"], self.live_dataset_version, self.runtime_version])
        snapshot["league"] = fixture["league"]
        snapshot["weights_version"] = self.version
        snapshot["goal_component_versions"] = components
        snapshot["fixture_id"] = fixture["fixture_id"]
        feature = {"id": "feature-"+sha([snapshot["snapshot_id"], row["features"]]), "fixture_id": fixture["fixture_id"], "cutoff_date": self.information_cutoff, "available_at": self.generated_at, "schema_version": "features-v3", "dataset_version": self.live_dataset_version, "values": row["features"], "weights_training_cutoff": self.meta["training_cutoff_exclusive"], "source_observation_ids": [r["observation_id"] for r in self.matches if r.get("observation_id") and r["date"] < self.information_cutoff]}
        return snapshot, feature
