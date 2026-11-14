"""Runs the agent on every eval ticket and scores it with the hidden tests.

    python -m evals.run_evals                    # all cases, Docker sandbox
    python -m evals.run_evals --only 01 05       # just some cases
    python -m evals.run_evals --sandbox local    # no Docker (not isolated)

A case passes only when BOTH are true:
  * the hidden test for that ticket passes
  * the app's own tests (as the agent left them) pass

The spec approval step is switched to auto approve here, so the numbers measure
the agent alone, with no human help.

Results go to evals/results/latest.json and evals/results/latest.md.
Each run is also saved to runs/ so the replay demo can show it.
"""
import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

from agent.cli import load_env
from agent.config import Settings
from agent.llm import ChatLLM
from agent.publish import LocalPublisher
from agent.runner import run_ticket, save_record
from agent.sandbox import make_sandbox

from .common import ROOT, SAMPLE_APP, fresh_copy, load_cases, run_hidden_test

RESULTS_DIR = ROOT / "evals" / "results"


def run_case(case, settings, sandbox, llm_factory, tmp: Path) -> dict:
    repo = fresh_copy(SAMPLE_APP, tmp / case.name / "repo")
    llm = llm_factory()
    record = run_ticket(
        case.title, case.body, repo, llm, sandbox,
        LocalPublisher(tmp / case.name / "out"), settings, run_id=f"eval-{case.name}",
    )
    hidden = run_hidden_test(case, repo, sandbox)
    own = sandbox.run_tests(repo)
    record["eval"] = {
        "case": case.name,
        "level": case.level,
        "hidden_passed": hidden.passed,
        "own_tests_passed": own.passed,
        "passed": hidden.passed and own.passed,
        "hidden_output": "" if hidden.passed else hidden.output[-2000:],
        "flagged_suspicious_text": bool(record["ticket"].get("suspicious")),
    }
    return record


def summarise(records: list, settings: Settings) -> dict:
    passed = [r for r in records if r["eval"]["passed"]]
    by_level = {}
    for record in records:
        level = by_level.setdefault(record["eval"]["level"], {"passed": 0, "total": 0})
        level["total"] += 1
        level["passed"] += record["eval"]["passed"]
    count = len(records) or 1
    return {
        "model": settings.model,
        "date": time.strftime("%Y-%m-%d"),
        "cases": len(records),
        "passed": len(passed),
        "pass_rate": round(len(passed) / count, 3),
        "passed_first_attempt": sum(1 for r in passed if r["attempts"] == 1),
        # A false pass is the worst result: the agent said "done" but the ticket is not solved.
        "false_passes": sum(1 for r in records if r["status"] == "pr_opened" and not r["eval"]["passed"]),
        "gave_up": sum(1 for r in records if r["status"] == "gave_up"),
        "errors": sum(1 for r in records if r["status"] == "error"),
        "by_level": by_level,
        "avg_seconds": round(sum(r["seconds"] for r in records) / count, 1),
        "avg_tokens": round(sum(r["tokens_in"] + r["tokens_out"] for r in records) / count),
        "total_cost_usd": round(sum(r["cost_usd"] for r in records), 4),
    }


def to_markdown(summary: dict, records: list) -> str:
    lines = [
        f"# Eval results ({summary['date']})",
        "",
        f"Model: `{summary['model']}`",
        "",
        f"- Passed: **{summary['passed']} of {summary['cases']}** ({summary['pass_rate']:.0%})",
        f"- Passed on the first attempt: {summary['passed_first_attempt']}",
        f"- False passes (opened a PR but the hidden test failed): {summary['false_passes']}",
        f"- Gave up cleanly: {summary['gave_up']}",
        f"- Errors: {summary['errors']}",
        f"- Average time per ticket: {summary['avg_seconds']}s",
        f"- Average tokens per ticket: {summary['avg_tokens']}",
        f"- Total cost: ${summary['total_cost_usd']} (0 means prices were not set)",
        "",
        "| Case | Level | Result | Agent status | Attempts | Seconds | Tokens |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in records:
        e = r["eval"]
        lines.append(
            f"| {e['case']} | {e['level']} | {'pass' if e['passed'] else 'FAIL'} | {r['status']} "
            f"| {r['attempts']} | {r['seconds']} | {r['tokens_in'] + r['tokens_out']} |"
        )
    return "\n".join(lines) + "\n"


def main(argv=None, llm_factory=None) -> int:
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", default=[])
    parser.add_argument("--sandbox", choices=["docker", "local"], default="docker")
    args = parser.parse_args(argv)

    settings = Settings()
    settings.auto_approve = True
    sandbox = make_sandbox(args.sandbox, settings.test_timeout_seconds)
    llm_factory = llm_factory or (lambda: ChatLLM(settings.model))

    records = []
    with tempfile.TemporaryDirectory() as tmp:
        for case in load_cases(args.only):
            print(f"{case.name} ... ", end="", flush=True)
            record = run_case(case, settings, sandbox, llm_factory, Path(tmp))
            records.append(record)
            save_record(record, ROOT / "runs")
            print(f"{'pass' if record['eval']['passed'] else 'FAIL'} "
                  f"({record['status']}, {record['attempts']} attempts, {record['seconds']}s)")

    summary = summarise(records, settings)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "latest.json").write_text(json.dumps({"summary": summary, "cases": [
        {**r["eval"], "status": r["status"], "attempts": r["attempts"], "seconds": r["seconds"],
         "tokens": r["tokens_in"] + r["tokens_out"], "failure_reason": r["failure_reason"] or r["error"]}
        for r in records]}, indent=2))
    (RESULTS_DIR / "latest.md").write_text(to_markdown(summary, records))
    print(f"\nPassed {summary['passed']} of {summary['cases']}. See evals/results/latest.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
