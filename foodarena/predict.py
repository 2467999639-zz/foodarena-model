import argparse
import json
from pathlib import Path

from .ranker import ROOT, read_json, recommend


def main():
    parser = argparse.ArgumentParser(description="Rank meals from a JSON request")
    parser.add_argument("--input", type=Path, default=ROOT / "examples" / "request.json")
    args = parser.parse_args()
    print(json.dumps(recommend(read_json(args.input)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
