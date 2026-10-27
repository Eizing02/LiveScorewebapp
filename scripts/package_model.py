import hashlib
import os
import zipfile

from ml.pipeline import ROOT
from ml.registry import verify


def main():
    version = os.environ["MODEL_VERSION"]
    verify(version)
    target = ROOT / "reports" / f"{version}.zip"
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted((ROOT / "ml/models" / version).iterdir()):
            archive.write(file, arcname=version + "/" + file.name)
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".zip.sha256").write_text(checksum + "  " + target.name + "\n", encoding="utf-8")
    print("Verified and packaged " + version)


if __name__ == "__main__":
    main()
