import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List

from agent.sandbox import Sandbox, TestResult

ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = ROOT / "evals" / "cases"
SAMPLE_APP = ROOT / "sample_app"
REFERENCE = ROOT / "evals" / "reference_solution"
HIDDEN_DIR = "tests_hidden"
IGNORE = shutil.ignore_patterns("__pycache__", ".pytest_cache", "README.md")


@dataclass
class Case:
    name: str
    level: str
    title: str
    body: str
    hidden_test: Path


def load_cases(only: List[str] = ()) -> List[Case]:
    cases = []
    for folder in sorted(CASES_DIR.iterdir()):
        if not folder.is_dir() or (only and not any(o in folder.name for o in only)):
            continue
        lines = (folder / "issue.md").read_text().strip().splitlines()
        cases.append(
            Case(
                name=folder.name,
                level=(folder / "level.txt").read_text().strip(),
                title=lines[0].lstrip("# ").strip(),
                body="\n".join(lines[1:]).strip(),
                hidden_test=folder / "test_hidden.py",
            )
        )
    return cases


def fresh_copy(source: Path, target: Path) -> Path:
    shutil.copytree(source, target, ignore=IGNORE)
    return target


def run_hidden_test(case: Case, repo: Path, sandbox: Sandbox) -> TestResult:
    """Drop the hidden test into the repo and run only that."""
    hidden = repo / HIDDEN_DIR
    hidden.mkdir(exist_ok=True)
    shutil.copy(ROOT / "evals" / "hidden_conftest.py", hidden / "conftest.py")
    shutil.copy(case.hidden_test, hidden / "test_hidden.py")
    try:
        return sandbox.run_tests(repo, extra_args=[HIDDEN_DIR])
    finally:
        shutil.rmtree(hidden)
