"""File access for the agent, with guard rails.

Every write the model asks for goes through `check_write`. The model never
gets a shell and never touches the file system on its own.
"""
import difflib
import re
from pathlib import Path
from typing import Dict, List, Optional

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules", ".mypy_cache"}
ALLOWED_SUFFIXES = {".py", ".md", ".txt", ".toml", ".ini", ".cfg", ".json", ".yaml", ".yml"}
# Places the agent may never write to, even if a ticket asks for it.
DENIED_PREFIXES = (".git/", ".github/")
DENIED_NAMES = {".env", ".netrc", "id_rsa", "credentials.json"}


class WriteRejected(Exception):
    pass


def list_files(repo: Path) -> List[str]:
    out = []
    for path in sorted(repo.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(repo)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        out.append(rel.as_posix())
    return out


def read_file(repo: Path, rel_path: str, max_bytes: int = 100_000) -> Optional[str]:
    try:
        target = _resolve_inside(repo, rel_path)
    except WriteRejected:
        return None
    if not target.is_file() or target.stat().st_size > max_bytes:
        return None
    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def _resolve_inside(repo: Path, rel_path: str) -> Path:
    if not rel_path or rel_path.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", rel_path):
        raise WriteRejected(f"{rel_path!r}: path must be relative to the repo")
    repo_root = repo.resolve()
    target = (repo_root / rel_path).resolve()
    if repo_root != target and repo_root not in target.parents:
        raise WriteRejected(f"{rel_path!r}: path leaves the repo")
    return target


def check_write(repo: Path, rel_path: str, content: str, max_bytes: int) -> Path:
    """Return the full path if the write is allowed, else raise WriteRejected."""
    target = _resolve_inside(repo, rel_path)
    rel = target.relative_to(repo.resolve()).as_posix()
    if any(rel == p.rstrip("/") or rel.startswith(p) for p in DENIED_PREFIXES):
        raise WriteRejected(f"{rel}: this folder is off limits")
    if target.name in DENIED_NAMES:
        raise WriteRejected(f"{rel}: this file is off limits")
    if target.suffix not in ALLOWED_SUFFIXES:
        raise WriteRejected(f"{rel}: file type {target.suffix or '(none)'} is not allowed")
    if len(content.encode("utf-8")) > max_bytes:
        raise WriteRejected(f"{rel}: file is larger than {max_bytes} bytes")
    if target.is_symlink():
        raise WriteRejected(f"{rel}: will not write through a symlink")
    return target


def write_file(repo: Path, rel_path: str, content: str, max_bytes: int) -> None:
    target = check_write(repo, rel_path, content, max_bytes)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def count_tests(repo: Path) -> int:
    """Count test functions. Used to stop the agent from deleting tests to go green."""
    total = 0
    for rel in list_files(repo):
        name = Path(rel).name
        if name.startswith("test_") and name.endswith(".py"):
            text = read_file(repo, rel) or ""
            total += len(re.findall(r"^\s*(?:async\s+)?def test_", text, re.MULTILINE))
    return total


def make_diff(repo: Path, originals: Dict[str, Optional[str]]) -> str:
    """Unified diff between the first seen version of each file and what is on disk now."""
    chunks = []
    for rel in sorted(originals):
        before = originals[rel] or ""
        after = read_file(repo, rel) or ""
        if before == after:
            continue
        chunks.extend(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"a/{rel}" if originals[rel] is not None else "/dev/null",
                tofile=f"b/{rel}",
            )
        )
    return "".join(chunks)
