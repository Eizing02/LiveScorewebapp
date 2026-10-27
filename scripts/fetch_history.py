import subprocess
from pathlib import Path

from ml.pipeline import POLICY, ROOT


def main():
    target = ROOT / "data/source/openfootball"
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--filter=blob:none", "https://github.com/openfootball/football.json.git", str(target)], check=True)
        subprocess.run(["git", "-C", str(target), "checkout", "--detach", POLICY["source_commit"]], check=True)
    actual = subprocess.check_output(["git", "-C", str(target), "rev-parse", "HEAD"], text=True).strip()
    if actual != POLICY["source_commit"]:
        raise ValueError("Existing snapshot differs; no automatic reset or overwrite.")
    if not (Path(target) / "LICENSE.md").exists():
        raise ValueError("source_license_missing")
    print("Pinned historical source verified: " + actual)


if __name__ == "__main__":
    main()
