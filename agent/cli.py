"""Command line entry point.

    python -m agent.cli local  --ticket path/to/ticket.md --repo sample_app
    python -m agent.cli github --repo owner/name --issue 12 --subdir sample_app
"""
import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

from .config import Settings
from .llm import ChatLLM
from .publish import GitHubClient, GitHubPublisher, LocalPublisher, git
from .runner import run_ticket, save_record
from .sandbox import make_sandbox

RUNS_DIR = Path("runs")


def load_env(path: Path = Path(".env")) -> None:
    """Tiny .env reader so the project has one less dependency."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def console_approver(payload: dict) -> dict:
    print("\n" + "=" * 70)
    print("SPEC FOR REVIEW")
    print("=" * 70)
    print(payload["spec"])
    if payload.get("suspicious"):
        print("\n!! The ticket has text that looks like instructions to the agent:")
        for item in payload["suspicious"]:
            print(f"   - {item}")
    print("=" * 70)
    while True:
        choice = input("[a]pprove, [e]dit from file, [r]evise with feedback, [x] reject: ").strip().lower()
        if choice == "a":
            return {"action": "approve"}
        if choice == "e":
            path = Path(input("Path to your edited spec file: ").strip())
            if path.is_file():
                return {"action": "edit", "spec": path.read_text()}
            print("File not found.")
        elif choice == "r":
            return {"action": "revise", "feedback": input("What should change? ").strip()}
        elif choice == "x":
            return {"action": "reject", "feedback": input("Reason (optional): ").strip()}


def split_ticket(text: str):
    """First line is the title (a leading '# ' is dropped). The rest is the body."""
    lines = text.strip().splitlines()
    title = lines[0].lstrip("# ").strip() if lines else "Untitled"
    return title, "\n".join(lines[1:]).strip()


def print_result(record: dict, path: Path) -> None:
    print(f"\nStatus:   {record['status']}")
    if record["failure_reason"] or record["error"]:
        print(f"Reason:   {record['failure_reason'] or record['error']}")
    if record["pr_url"]:
        print(f"Result:   {record['pr_url']}")
    print(f"Attempts: {record['attempts']}")
    print(f"Tokens:   {record['tokens_in']} in, {record['tokens_out']} out")
    print(f"Time:     {record['seconds']}s")
    print(f"Record:   {path}")


def cmd_local(args, settings: Settings) -> int:
    title, body = split_ticket(Path(args.ticket).read_text())
    work = Path(tempfile.mkdtemp(prefix="ticket-agent-")) / "repo"
    shutil.copytree(args.repo, work, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    print(f"Working on a copy of {args.repo} at {work}")
    llm = ChatLLM(settings.model)
    record = run_ticket(
        title, body, work, llm,
        make_sandbox(args.sandbox, settings.test_timeout_seconds),
        LocalPublisher(work.parent / "out"),
        settings,
        approver=console_approver,
    )
    print_result(record, save_record(record, RUNS_DIR))
    if record["diff"]:
        print("\n" + record["diff"])
    return 0 if record["status"] == "pr_opened" else 1


def cmd_github(args, settings: Settings) -> int:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Set GITHUB_TOKEN in your .env (needs contents, issues and pull request write access).")
        return 2
    client = GitHubClient(args.repo, token)
    issue = client.get_issue(args.issue)
    clone_dir = Path(tempfile.mkdtemp(prefix="ticket-agent-")) / "clone"
    git(["clone", "--depth", "1", f"https://github.com/{args.repo}.git", str(clone_dir)],
        Path.cwd(), token=token)
    repo_path = clone_dir / args.subdir if args.subdir else clone_dir
    llm = ChatLLM(settings.model)
    record = run_ticket(
        issue["title"], issue.get("body") or "", repo_path, llm,
        make_sandbox(args.sandbox, settings.test_timeout_seconds),
        GitHubPublisher(client, clone_dir, args.issue, token),
        settings,
        approver=console_approver,
    )
    print_result(record, save_record(record, RUNS_DIR))
    return 0 if record["status"] == "pr_opened" else 1


def main(argv=None) -> int:
    load_env()
    parser = argparse.ArgumentParser(prog="agent")
    sub = parser.add_subparsers(dest="command", required=True)

    local = sub.add_parser("local", help="Run on a ticket file and a local folder")
    local.add_argument("--ticket", required=True)
    local.add_argument("--repo", default="sample_app")
    local.add_argument("--sandbox", choices=["docker", "local"], default="docker")
    local.set_defaults(func=cmd_local)

    github = sub.add_parser("github", help="Run on a real GitHub issue and open a pull request")
    github.add_argument("--repo", required=True, help="owner/name")
    github.add_argument("--issue", type=int, required=True)
    github.add_argument("--subdir", default="", help="Folder inside the repo that holds the app")
    github.add_argument("--sandbox", choices=["docker", "local"], default="docker")
    github.set_defaults(func=cmd_github)

    args = parser.parse_args(argv)
    return args.func(args, Settings())


if __name__ == "__main__":
    sys.exit(main())
