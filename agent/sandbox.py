"""Where the tests run.

Code written by a model is untrusted code. The Docker sandbox runs it with
no network, a read-only copy of the repo, and limits on memory, CPU and
process count. The local sandbox is only for quick development and for this
project's own unit tests.
"""
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Protocol

TAIL_CHARS = 6000


@dataclass
class TestResult:
    __test__ = False  # tell pytest this is not a test class

    passed: bool
    output: str


class Sandbox(Protocol):
    def run_tests(self, repo: Path, extra_args: List[str] = ()) -> TestResult: ...


def _finish(cmd: List[str], cwd: Path, timeout: int, env: dict) -> TestResult:
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env
        )
    except subprocess.TimeoutExpired:
        return TestResult(False, f"Tests did not finish within {timeout} seconds.")
    output = (proc.stdout + "\n" + proc.stderr).strip()
    # Exit code 5 means "no tests collected". Treat that as a failure.
    return TestResult(proc.returncode == 0, output[-TAIL_CHARS:])


PYTEST_ARGS = ["-q", "--no-header", "-p", "no:cacheprovider"]


class DockerSandbox:
    def __init__(self, image: str = "ticket-agent-sandbox", timeout: int = 180):
        self.image = image
        self.timeout = timeout

    def run_tests(self, repo: Path, extra_args: List[str] = ()) -> TestResult:
        cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", "1g",
            "--cpus", "1",
            "--pids-limit", "256",
            "--read-only",
            "--tmpfs", "/tmp",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-v", f"{repo.resolve()}:/work:ro",
            "-w", "/work",
            self.image,
            "python", "-m", "pytest", *PYTEST_ARGS, *extra_args,
        ]
        # The docker command itself needs the normal environment to find the
        # daemon. The container does not inherit it: only the "-e" values above
        # get inside, so no tokens or keys reach the code under test.
        return _finish(cmd, repo, self.timeout, dict(os.environ))


class LocalSandbox:
    """Runs pytest as a plain child process. Not isolated. Do not use on real tickets."""

    def __init__(self, timeout: int = 180):
        self.timeout = timeout

    def run_tests(self, repo: Path, extra_args: List[str] = ()) -> TestResult:
        cmd = [sys.executable, "-m", "pytest", *PYTEST_ARGS, *extra_args]
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "HOME": os.environ.get("HOME", ""),
        }
        return _finish(cmd, repo, self.timeout, env)


def make_sandbox(kind: str, timeout: int) -> Sandbox:
    if kind == "docker":
        return DockerSandbox(timeout=timeout)
    if kind == "local":
        return LocalSandbox(timeout=timeout)
    raise ValueError(f"Unknown sandbox: {kind}")
