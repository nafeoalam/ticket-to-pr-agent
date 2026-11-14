"""Proves the eval cases are fair. Needs no model and no API key.

For every case:
  * the hidden test must FAIL on the starting app (so the ticket is real work)
  * the hidden test must PASS on the reference solution (so the ticket can be solved)

    python -m evals.check_cases
"""
import sys
import tempfile
from pathlib import Path

from agent.sandbox import LocalSandbox

from .common import REFERENCE, SAMPLE_APP, fresh_copy, load_cases, run_hidden_test


def main() -> int:
    sandbox = LocalSandbox()
    problems = 0
    with tempfile.TemporaryDirectory() as tmp:
        base = fresh_copy(SAMPLE_APP, Path(tmp) / "base")
        solved = fresh_copy(REFERENCE, Path(tmp) / "solved")

        own_tests = sandbox.run_tests(solved)
        if not own_tests.passed:
            print("Reference solution fails its own tests:\n" + own_tests.output)
            return 1

        for case in load_cases():
            fails_on_base = not run_hidden_test(case, base, sandbox).passed
            on_solved = run_hidden_test(case, solved, sandbox)
            ok = fails_on_base and on_solved.passed
            problems += not ok
            print(f"{'ok  ' if ok else 'BAD '} {case.name:32} "
                  f"fails on start: {fails_on_base}, passes on reference: {on_solved.passed}")
            if not on_solved.passed:
                print(on_solved.output)
    print(f"\n{problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
