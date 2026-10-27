"""Build the display catalogue from existing cache; optional loopback-only import."""
import argparse
import json
from urllib.parse import urlsplit

from ml.program_catalog import OUTPUT, build
from ml.provider_broker import BrokerClient


def run(import_local=False):
    summary = build()
    if import_local:
        broker = BrokerClient()
        if urlsplit(broker.base).hostname not in {"127.0.0.1", "localhost"}:
            raise ValueError("program_import_is_local_only")
        for batch in json.loads((OUTPUT / "import-batches.json").read_text(encoding="utf-8")):
            broker.request("program_import", {"records": batch})
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--import-local", action="store_true")
    print(json.dumps(run(parser.parse_args().import_local)))
