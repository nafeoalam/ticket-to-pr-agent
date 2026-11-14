"""The agent flow as a LangGraph state machine.

    parse_ticket -> explore -> write_spec -> approval -> implement -> run_tests
                                   ^            |            ^           |
                                   +-- revise --+            +-- retry --+
                                                |                        |
                                             rejected            open_pr / give_up
"""
import time
from functools import wraps
from pathlib import Path
from typing import Callable

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from . import prompts, repo_tools
from .config import Settings
from .llm import LLM, ModelOutputError, extract_json
from .publish import Publisher
from .sandbox import Sandbox
from .state import AgentState

MAX_SPEC_ROUNDS = 3


def build_graph(
    llm: LLM,
    sandbox: Sandbox,
    publisher: Publisher,
    settings: Settings,
    checkpointer=None,
):
    def logged(name: str) -> Callable:
        """Record time and tokens for a step. This is what the replay demo shows."""

        def decorator(fn):
            @wraps(fn)
            def wrapper(state: AgentState) -> dict:
                started = time.time()
                tokens_in, tokens_out = llm.usage.input_tokens, llm.usage.output_tokens
                update = fn(state)  # an interrupt passes straight through here
                entry = {
                    "step": name,
                    "seconds": round(time.time() - started, 2),
                    "tokens_in": llm.usage.input_tokens - tokens_in,
                    "tokens_out": llm.usage.output_tokens - tokens_out,
                    "summary": update.pop("_summary", ""),
                }
                update["log"] = [entry]
                return update

            return wrapper

        return decorator

    def ask_json(step: str, system: str, user: str):
        """Call the model and parse JSON. One repair try if the JSON is broken."""
        reply = llm.complete(step, system, user)
        try:
            return extract_json(reply)
        except ModelOutputError:
            reply = llm.complete(
                step,
                system,
                user + "\n\nYour last reply was not valid JSON. Reply again with JSON only.",
            )
            return extract_json(reply)

    def read_chosen_files(state: AgentState) -> dict:
        repo = Path(state["repo_path"])
        contents = {}
        for rel in state.get("files", []):
            text = repo_tools.read_file(repo, rel, settings.max_file_bytes)
            if text is not None:
                contents[rel] = text
        return contents

    # ------------------------------------------------------------------ steps

    @logged("parse_ticket")
    def parse_ticket(state: AgentState) -> dict:
        block = prompts.ticket_block(state["ticket_title"], state["ticket_body"])
        ticket = ask_json("parse_ticket", prompts.PARSE_TICKET_SYSTEM, block)
        ticket.setdefault("summary", state["ticket_title"])
        ticket.setdefault("acceptance_criteria", [])
        ticket.setdefault("suspicious", [])
        return {"ticket": ticket, "_summary": ticket["summary"]}

    @logged("explore")
    def explore(state: AgentState) -> dict:
        repo = Path(state["repo_path"])
        all_files = repo_tools.list_files(repo)
        system = prompts.PICK_FILES_SYSTEM.replace("{max_files}", str(settings.max_files_read))
        user = (
            f"Ticket summary: {state['ticket']['summary']}\n"
            f"Acceptance criteria: {state['ticket']['acceptance_criteria']}\n\n"
            "Files in the repo:\n" + "\n".join(all_files)
        )
        picked = ask_json("explore", system, user).get("files", [])
        # Keep only real files, in case the model made one up.
        known = set(all_files)
        files = [f for f in picked if f in known][: settings.max_files_read]
        return {
            "files": files,
            "tests_before": repo_tools.count_tests(repo),
            "_summary": f"Reading {len(files)} of {len(all_files)} files",
        }

    @logged("write_spec")
    def write_spec(state: AgentState) -> dict:
        user = (
            prompts.ticket_block(state["ticket_title"], state["ticket_body"])
            + f"\n\nAcceptance criteria: {state['ticket']['acceptance_criteria']}\n\n"
            + prompts.files_block(read_chosen_files(state))
        )
        if state.get("spec_feedback"):
            user += (
                f"\n\nYour earlier spec:\n{state.get('spec', '')}\n\n"
                f"The reviewer asked for changes:\n{state['spec_feedback']}"
            )
        spec = llm.complete("write_spec", prompts.WRITE_SPEC_SYSTEM, user).strip()
        return {
            "spec": spec,
            "spec_rounds": state.get("spec_rounds", 0) + 1,
            "_summary": f"Spec written ({len(spec.split())} words)",
        }

    @logged("approval")
    def approval(state: AgentState) -> dict:
        if settings.auto_approve:
            return {"spec_feedback": "", "_summary": "Auto approved (eval mode)"}
        # The run stops here and its state is saved. It continues when a human
        # answers. The answer is a dict: {"action": ..., "spec": ..., "feedback": ...}
        answer = interrupt(
            {
                "spec": state["spec"],
                "suspicious": state["ticket"].get("suspicious", []),
                "actions": ["approve", "edit", "revise", "reject"],
            }
        )
        action = answer.get("action")
        if action == "approve":
            return {"spec_feedback": "", "_summary": "Approved by reviewer"}
        if action == "edit":
            return {"spec": answer["spec"], "spec_feedback": "", "_summary": "Reviewer edited the spec"}
        if action == "revise" and state.get("spec_rounds", 0) < MAX_SPEC_ROUNDS:
            return {"spec_feedback": answer.get("feedback", ""), "_summary": "Reviewer asked for a new spec"}
        reason = answer.get("feedback") or "Reviewer rejected the spec"
        return {"status": "rejected", "failure_reason": reason, "_summary": reason}

    @logged("implement")
    def implement(state: AgentState) -> dict:
        repo = Path(state["repo_path"])
        user = (
            prompts.ticket_block(state["ticket_title"], state["ticket_body"])
            + f"\n\nApproved spec:\n{state['spec']}\n\n"
            + "Current files:\n"
            + prompts.files_block(read_chosen_files(state))
        )
        if state.get("attempts", 0) > 0:
            user += f"\n\nYour last attempt failed. Test output:\n{state.get('test_output', '')}"
            if state.get("rejected_writes"):
                user += "\n\nThese writes were blocked:\n" + "\n".join(state["rejected_writes"])

        attempts = state.get("attempts", 0) + 1
        try:
            result = ask_json("implement", prompts.IMPLEMENT_SYSTEM, user)
            changes = result.get("files", [])
        except ModelOutputError as exc:
            return {"attempts": attempts, "rejected_writes": [str(exc)], "_summary": "No usable reply"}

        originals = dict(state.get("originals", {}))
        files = list(state.get("files", []))
        rejected = []
        written = 0
        if len(changes) > settings.max_files_changed:
            rejected.append(f"Too many files in one attempt (limit {settings.max_files_changed})")
            changes = []
        for change in changes:
            rel, content = change.get("path", ""), change.get("content", "")
            try:
                repo_tools.check_write(repo, rel, content, settings.max_file_bytes)
            except repo_tools.WriteRejected as exc:
                rejected.append(str(exc))
                continue
            if rel not in originals:
                originals[rel] = repo_tools.read_file(repo, rel, settings.max_file_bytes)
            repo_tools.write_file(repo, rel, content, settings.max_file_bytes)
            if rel not in files:
                files.append(rel)  # show new files to the next attempt
            written += 1
        return {
            "attempts": attempts,
            "originals": originals,
            "files": files,
            "notes": result.get("notes", ""),
            "rejected_writes": rejected,
            "_summary": f"Attempt {attempts}: wrote {written} files, blocked {len(rejected)}",
        }

    @logged("run_tests")
    def run_tests(state: AgentState) -> dict:
        repo = Path(state["repo_path"])
        tests_now = repo_tools.count_tests(repo)
        if tests_now < state.get("tests_before", 0):
            # Guard against "fixing" a red build by removing tests.
            output = (
                f"Blocked: the change removed tests ({state['tests_before']} before, "
                f"{tests_now} now). Restore them. Update a test only when the spec "
                "changes the behaviour it checks."
            )
            return {"tests_passed": False, "test_output": output, "_summary": "Tests were removed"}
        result = sandbox.run_tests(repo)
        return {
            "tests_passed": result.passed,
            "test_output": result.output,
            "diff": repo_tools.make_diff(repo, state.get("originals", {})),
            "_summary": "Tests passed" if result.passed else "Tests failed",
        }

    @logged("open_pr")
    def open_pr(state: AgentState) -> dict:
        ticket = state["ticket"]
        title = ticket["summary"][:72]
        criteria = "\n".join(f"- {c}" for c in ticket.get("acceptance_criteria", [])) or "- (none listed)"
        body = (
            f"## What this does\n{state.get('notes', '')}\n\n"
            f"## Acceptance criteria\n{criteria}\n\n"
            f"## Spec (approved by a human before any code was written)\n{state['spec']}\n\n"
            f"## Test results\nPassed on attempt {state['attempts']} of {settings.max_attempts}.\n\n"
            f"```\n{state.get('test_output', '')[-1500:]}\n```\n\n"
            "_Opened by ticket-to-pr-agent. Please review like any other pull request._"
        )
        url = publisher.open_pr(title, body)
        return {"status": "pr_opened", "pr_title": title, "pr_body": body, "pr_url": url, "_summary": url}

    @logged("give_up")
    def give_up(state: AgentState) -> dict:
        if llm.usage.total_tokens >= settings.max_tokens_per_ticket:
            reason = f"Token budget for one ticket was used up ({settings.max_tokens_per_ticket})"
        else:
            reason = f"Tests still failing after {state.get('attempts', 0)} attempts"
        comment = (
            "I could not finish this ticket, so I did not open a pull request.\n\n"
            f"**Why:** {reason}\n\n"
            f"**Last test output:**\n```\n{state.get('test_output', '')[-1500:]}\n```\n\n"
            "A person should pick this up from here."
        )
        publisher.report_failure(comment)
        return {"status": "gave_up", "failure_reason": reason, "_summary": reason}

    # ----------------------------------------------------------------- routes

    def after_approval(state: AgentState) -> str:
        if state.get("status") == "rejected":
            return "end"
        if state.get("spec_feedback"):
            return "write_spec"
        return "implement"

    def after_tests(state: AgentState) -> str:
        if state.get("tests_passed"):
            return "open_pr"
        out_of_tries = state.get("attempts", 0) >= settings.max_attempts
        out_of_budget = llm.usage.total_tokens >= settings.max_tokens_per_ticket
        return "give_up" if out_of_tries or out_of_budget else "implement"

    builder = StateGraph(AgentState)
    for name, fn in [
        ("parse_ticket", parse_ticket),
        ("explore", explore),
        ("write_spec", write_spec),
        ("approval", approval),
        ("implement", implement),
        ("run_tests", run_tests),
        ("open_pr", open_pr),
        ("give_up", give_up),
    ]:
        builder.add_node(name, fn)

    builder.add_edge(START, "parse_ticket")
    builder.add_edge("parse_ticket", "explore")
    builder.add_edge("explore", "write_spec")
    builder.add_edge("write_spec", "approval")
    builder.add_conditional_edges(
        "approval", after_approval, {"end": END, "write_spec": "write_spec", "implement": "implement"}
    )
    builder.add_edge("implement", "run_tests")
    builder.add_conditional_edges(
        "run_tests", after_tests, {"open_pr": "open_pr", "give_up": "give_up", "implement": "implement"}
    )
    builder.add_edge("open_pr", END)
    builder.add_edge("give_up", END)

    return builder.compile(checkpointer=checkpointer or InMemorySaver())
