import os
import subprocess

from ml.pipeline import ROOT
from ml.registry import verify


def main():
    version = os.environ["MODEL_VERSION"]
    verify(version)
    archive = ROOT / "reports" / f"{version}.zip"
    # Only invoked by the explicitly approved release workflow; no shell interpolation.
    subprocess.run(["gh", "release", "create", "model-" + version, str(archive), str(archive.with_suffix(".zip.sha256")), "--title", "Model candidate " + version, "--notes", "Immutable reviewed candidate. Not automatically promoted."], check=True)


if __name__ == "__main__":
    main()
