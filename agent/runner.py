"""Runs one ticket through the graph and returns a record of what happened."""
import json
import time
import uuid
from pathlib import Path
from typing import Callable, Optional

from langgraph.types import Command

from .config import Settings
from .graph import build_graph
from .llm import LLM
from .publish import Publisher
from .sandbox import Sandbox

Approver = Callable[[dict], dict]


def run_ticket(
    title: str,
    body: str,
    repo_path: Path,
    llm: LLM,
    sandbox: Sandbox,
    publisher: Publisher,
    settings: Settings,
    approver: Optional[Approver] = None,
    run_id: Optional[str] = None,
) -> dict:
    run_id = run_id or uuid.uuid4().hex[:8]
    graph = build_graph(llm, sandbox, publisher, settings)
    config = {"configurable": {"thread_id": run_id}, "recursion_limit": 60}
    started = time.time()
    error = ""
    state: dict = {}
    try:
        result = graph.invoke(
            {"ticket_title": title, "ticket_body": body, "repo_path": str(repo_path)}, config
        )
        # Each time the graph pauses for a human, ask the approver and resume.
        while result.get("__interrupt__"):
            if approver is None:
                raise RuntimeError("The run needs a human answer but no approver was given")
            answer = approver(result["__interrupt__"][0].value)
            result = graph.invoke(Command(resume=answer), config)
        state = result
    except Exception as exc:  # keep a record even when a run breaks
        error = f"{type(exc).__name__}: {exc}"
        state = dict(graph.get_state(config).values)

    return {
        "run_id": run_id,
        "ticket_title": title,
        "ticket_body": body,
        "status": state.get("status") or ("error" if error else "unknown"),
        "error": error,
        "failure_reason": state.get("failure_reason", ""),
        "ticket": state.get("ticket", {}),
        "spec": state.get("spec", ""),
        "attempts": state.get("attempts", 0),
        "tests_passed": bool(state.get("tests_passed")),
        "test_output": state.get("test_output", ""),
        "diff": state.get("diff", ""),
        "pr_title": state.get("pr_title", ""),
        "pr_body": state.get("pr_body", ""),
        "pr_url": state.get("pr_url", ""),
        "steps": state.get("log", []),
        "seconds": round(time.time() - started, 1),
        "llm_calls": llm.usage.calls,
        "tokens_in": llm.usage.input_tokens,
        "tokens_out": llm.usage.output_tokens,
        "cost_usd": round(
            llm.usage.cost(settings.price_in_per_mtok, settings.price_out_per_mtok), 4
        ),
        "model": settings.model,
    }


def save_record(record: dict, runs_dir: Path) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{record['run_id']}.json"
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return path
