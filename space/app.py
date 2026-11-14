"""Replay viewer for Hugging Face Spaces.

It does NOT run the agent. Running a coding agent for strangers on the open
internet is a security and cost problem, so this page only replays runs that
were recorded on my own machine.

To publish: copy the run records you want to show into space/runs/, then push
this folder to a Gradio Space.
"""
import json
from pathlib import Path
from typing import Dict, List

RUNS_DIR = Path(__file__).parent / "runs"


def load_runs(runs_dir: Path = RUNS_DIR) -> Dict[str, dict]:
    runs = {}
    for path in sorted(runs_dir.glob("*.json")):
        try:
            record = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        result = record.get("eval", {}).get("passed")
        mark = {True: "pass", False: "fail"}.get(result, record.get("status", "?"))
        runs[f"{record['run_id']}  [{mark}]  {record['ticket_title']}"] = record
    return runs


def steps_table(record: dict) -> List[list]:
    return [
        [i + 1, s["step"], s["summary"], s["seconds"], s["tokens_in"] + s["tokens_out"]]
        for i, s in enumerate(record.get("steps", []))
    ]


def overview(record: dict) -> str:
    lines = [
        f"### {record['ticket_title']}",
        f"**Status:** {record['status']}  |  **Attempts:** {record['attempts']}  |  "
        f"**Time:** {record['seconds']}s  |  "
        f"**Tokens:** {record['tokens_in'] + record['tokens_out']}  |  **Model:** `{record.get('model', '')}`",
    ]
    if record.get("eval"):
        lines.append(
            f"**Hidden test:** {'passed' if record['eval']['hidden_passed'] else 'failed'}  |  "
            f"**Level:** {record['eval']['level']}"
        )
    if record.get("failure_reason") or record.get("error"):
        lines.append(f"**Why it stopped:** {record.get('failure_reason') or record.get('error')}")
    suspicious = record.get("ticket", {}).get("suspicious")
    if suspicious:
        lines.append("**Flagged as suspicious in the ticket:** " + "; ".join(suspicious))
    return "\n\n".join(lines)


def show(label: str, runs: Dict[str, dict]):
    record = runs[label]
    return (
        overview(record),
        f"**{record['ticket_title']}**\n\n{record['ticket_body']}",
        record.get("spec", ""),
        record.get("diff", "") or "(no changes)",
        record.get("test_output", ""),
        steps_table(record),
    )


def build():
    import gradio as gr

    runs = load_runs()
    with gr.Blocks(title="Ticket to PR agent: replays") as demo:
        gr.Markdown(
            "# Ticket to pull request agent\n"
            "Replays of recorded runs. Pick a run to see the ticket, the spec the agent wrote, "
            "the code change, the test output and each step with its time and token use."
        )
        if not runs:
            gr.Markdown("No runs yet. Add run records to `space/runs/`.")
            return demo
        labels = list(runs)
        picker = gr.Dropdown(labels, value=labels[0], label="Run")
        summary = gr.Markdown()
        with gr.Tab("Ticket"):
            ticket = gr.Markdown()
        with gr.Tab("Spec"):
            spec = gr.Markdown()
        with gr.Tab("Code change"):
            diff = gr.Code(language=None, label="Diff")
        with gr.Tab("Test output"):
            tests = gr.Code(language=None, label="pytest")
        with gr.Tab("Steps"):
            steps = gr.Dataframe(headers=["#", "Step", "What happened", "Seconds", "Tokens"])
        outputs = [summary, ticket, spec, diff, tests, steps]
        picker.change(lambda label: show(label, runs), picker, outputs)
        demo.load(lambda: show(labels[0], runs), None, outputs)
    return demo


if __name__ == "__main__":
    build().launch()
