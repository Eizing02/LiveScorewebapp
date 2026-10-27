"""Separate CC-BY-SA audit, not a source of training labels or kickoff dates."""
import csv
import json
from collections import Counter, defaultdict

from ml.expanded import OUTPUT, map_name
from ml.pipeline import ROOT, write_json


def main():
    rows = [json.loads(line) for line in (OUTPUT / "accepted.jsonl").read_text(encoding="utf-8").splitlines()]
    vocab = defaultdict(set)
    lookup = {}
    for row in rows:
        if row["league"] in {"en.1", "en.2"}:
            vocab[row["league"]].update([row["home"], row["away"]])
            lookup[(row["league"], row["season"][:4], row["home"], row["away"])] = row
    counts, conflicts = Counter(), []
    with (ROOT / "data/source/additional/fjelstul/matches.csv").open(encoding="utf-8-sig", newline="") as stream:
        for reference in csv.DictReader(stream):
            if reference["tier"] not in {"1", "2"} or not "2021" <= reference["season"] <= "2026":
                continue
            league = "en." + reference["tier"]
            try:
                home, _ = map_name(reference["home_team_name"], vocab[league])
                away, _ = map_name(reference["away_team_name"], vocab[league])
            except ValueError:
                counts["unmapped_reference"] += 1
                continue
            row = lookup.get((league, reference["season"], home, away))
            if not row:
                counts["no_in_window_training_match"] += 1
                continue
            score = [int(reference["home_team_score"]), int(reference["away_team_score"])]
            if score == row["goals"]:
                counts["score_agreement"] += 1
            else:
                counts["score_disagreement"] += 1
                conflicts.append({"id": row["id"], "reference_id": reference["match_id"], "training_score": row["goals"], "reference_score": score})
    report = {"source": "Fjelstul English Football Database", "source_commit": "ff3c37698065476e1852243685da6b756a580b9f", "attribution": "Joshua C. Fjelstul, Ph.D.; © 2024 Joshua C. Fjelstul, Ph.D.", "url": "https://github.com/jfjelstul/englishfootball", "license": "CC-BY-SA-4.0", "license_url": "https://creativecommons.org/licenses/by-sa/4.0/", "modifications": "Filtered 2021 onward, matched regular-season ordered team pairs, compared scores; no reference rows redistributed here", "counts": dict(counts), "conflicts": conflicts, "limitations": ["Reference match CSV contains seasons, not match dates: cannot verify chronology or kickoff", "Different data provenance is not proof of statistical independence", "No reference labels merged into training; disagreements remain visible for review"]}
    write_json(ROOT / "reports/recent-v2-reference-crosscheck.json", report)
    print(json.dumps(dict(counts)))


if __name__ == "__main__":
    main()
