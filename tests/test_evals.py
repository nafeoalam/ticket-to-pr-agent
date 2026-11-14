"""Tests for the scoring code itself, using a scripted model."""
import json
from pathlib import Path

from agent.config import Settings
from agent.llm import FakeLLM
from agent.sandbox import LocalSandbox
from evals import check_cases
from evals.common import load_cases
from evals.run_evals import run_case, summarise, to_markdown

ROOT = Path(__file__).resolve().parent.parent
MAIN = (ROOT / "sample_app" / "app" / "main.py").read_text()

TICKET = json.dumps({"summary": "Fix typo", "kind": "bug", "acceptance_criteria": [], "suspicious": []})
FILES = json.dumps({"files": ["app/main.py"]})


def fake(main_content):
    change = json.dumps({"files": [{"path": "app/main.py", "content": main_content}], "notes": "n"})
    return lambda: FakeLLM(
        {"parse_ticket": [TICKET], "explore": [FILES], "write_spec": ["spec"], "implement": [change]}
    )


def settings():
    s = Settings(model="fake")
    s.auto_approve = True
    return s


def test_every_case_is_fair():
    assert check_cases.main() == 0


def test_there_are_enough_cases():
    cases = load_cases()
    assert len(cases) >= 15
    assert {c.level for c in cases} == {"easy", "medium", "hard", "safety"}


def test_a_real_fix_scores_as_a_pass(tmp_path):
    case = load_cases(["01_"])[0]
    fixed = MAIN.replace("Task not fonud", "Task not found")
    record = run_case(case, settings(), LocalSandbox(), fake(fixed), tmp_path)
    assert record["eval"]["passed"] is True


def test_a_change_that_misses_the_point_is_a_false_pass(tmp_path):
    # The app's own tests stay green, so the agent opens a PR, but the ticket is not solved.
    case = load_cases(["01_"])[0]
    record = run_case(case, settings(), LocalSandbox(), fake(MAIN + "\n# no real change\n"), tmp_path)
    assert record["status"] == "pr_opened"
    assert record["eval"]["passed"] is False
    summary = summarise([record], settings())
    assert summary["false_passes"] == 1
    assert "FAIL" in to_markdown(summary, [record])
