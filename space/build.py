"""Bundle the run records in space/runs/ into space/runs.json for the replay page.

    python space/build.py

The page is static (plain HTML, no server), so it cannot list a folder.
This script keeps only the fields the page shows and writes them to one file.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
FIELDS = [
    "run_id", "ticket_title", "ticket_body", "status", "attempts", "seconds",
    "tokens_in", "tokens_out", "cost_usd", "model", "spec", "diff", "test_output",
    "failure_reason", "error", "steps",
]


def slim(record: dict) -> dict:
    out = {key: record.get(key) for key in FIELDS}
    out["suspicious"] = record.get("ticket", {}).get("suspicious", [])
    if record.get("eval"):
        out["eval"] = {key: record["eval"][key] for key in ("case", "level", "passed", "hidden_passed")}
    return out


def main() -> None:
    records = [json.loads(p.read_text()) for p in sorted((HERE / "runs").glob("*.json"))]
    # Runs without an eval block were reviewed by a human, so show them first.
    records.sort(key=lambda r: (bool(r.get("eval")), r.get("eval", {}).get("case", "")))
    (HERE / "runs.json").write_text(json.dumps([slim(r) for r in records], indent=1))
    print(f"Wrote {len(records)} runs to {HERE / 'runs.json'}")


if __name__ == "__main__":
    main()
