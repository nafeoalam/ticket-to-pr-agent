import operator
from typing import Annotated, Dict, List, Optional, TypedDict


class AgentState(TypedDict, total=False):
    # Input
    ticket_title: str
    ticket_body: str
    repo_path: str

    # Filled in as the run moves along
    ticket: dict                 # parsed ticket: summary, kind, acceptance_criteria, suspicious
    files: List[str]             # files chosen for reading
    spec: str
    spec_feedback: str           # set when the human asks for a new spec
    spec_rounds: int
    originals: Dict[str, Optional[str]]  # first seen content of each changed file
    tests_before: int            # number of test functions before any change
    notes: str
    rejected_writes: List[str]
    attempts: int
    tests_passed: bool
    test_output: str
    diff: str

    # Result
    status: str                  # "pr_opened" | "gave_up" | "rejected"
    failure_reason: str
    pr_title: str
    pr_body: str
    pr_url: str

    # One record per step. The reducer appends instead of replacing.
    log: Annotated[List[dict], operator.add]
