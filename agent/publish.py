"""Where the result goes: a real GitHub pull request, or a local file."""
import base64
import subprocess
from pathlib import Path
from typing import Optional, Protocol

import requests

API = "https://api.github.com"


class Publisher(Protocol):
    def open_pr(self, title: str, body: str) -> str: ...
    def report_failure(self, body: str) -> None: ...


class LocalPublisher:
    """Writes the pull request text to disk. Used for local runs and evals."""

    def __init__(self, out_dir: Path):
        self.out_dir = out_dir

    def open_pr(self, title: str, body: str) -> str:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.out_dir / "pull_request.md"
        path.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
        return f"local://{path}"

    def report_failure(self, body: str) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        (self.out_dir / "failure_comment.md").write_text(body + "\n", encoding="utf-8")


class GitHubClient:
    def __init__(self, repo: str, token: str):
        self.repo = repo
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _call(self, method: str, path: str, **kwargs) -> dict:
        response = requests.request(
            method, f"{API}/repos/{self.repo}{path}", headers=self._headers, timeout=30, **kwargs
        )
        response.raise_for_status()
        return response.json()

    def get_issue(self, number: int) -> dict:
        return self._call("GET", f"/issues/{number}")

    def default_branch(self) -> str:
        return self._call("GET", "")["default_branch"]

    def create_pr(self, title: str, body: str, head: str, base: str) -> str:
        data = self._call(
            "POST", "/pulls", json={"title": title, "body": body, "head": head, "base": base}
        )
        return data["html_url"]

    def comment(self, issue_number: int, body: str) -> None:
        self._call("POST", f"/issues/{issue_number}/comments", json={"body": body})


def git(args: list, cwd: Path, token: Optional[str] = None) -> str:
    cmd = ["git"]
    if token:
        # The token is passed for this one command only. It is never written
        # to the repo config, so code running in the clone cannot read it.
        basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        cmd += ["-c", f"http.extraHeader=Authorization: Basic {basic}"]
    proc = subprocess.run(cmd + args, cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed: {proc.stderr.strip()}")
    return proc.stdout


class GitHubPublisher:
    """Commits the change on a new branch, pushes it and opens the pull request."""

    def __init__(self, client: GitHubClient, clone_dir: Path, issue_number: int, token: str):
        self.client = client
        self.clone_dir = clone_dir
        self.issue_number = issue_number
        self._token = token
        self.branch = f"agent/issue-{issue_number}"

    def open_pr(self, title: str, body: str) -> str:
        base = self.client.default_branch()
        git(["checkout", "-b", self.branch], self.clone_dir)
        git(["add", "-A"], self.clone_dir)
        git(
            ["-c", "user.name=ticket-to-pr-agent", "-c", "user.email=agent@users.noreply.github.com",
             "commit", "-m", f"{title}\n\nCloses #{self.issue_number}"],
            self.clone_dir,
        )
        git(["push", "origin", self.branch], self.clone_dir, token=self._token)
        return self.client.create_pr(
            title, f"{body}\n\nCloses #{self.issue_number}", head=self.branch, base=base
        )

    def report_failure(self, body: str) -> None:
        self.client.comment(self.issue_number, body)
