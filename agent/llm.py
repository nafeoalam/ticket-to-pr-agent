"""A thin layer over the chat model.

The graph only needs one method: `complete(step, system, user) -> str`.
Keeping it this small makes it easy to swap in a fake model for tests.
"""
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Protocol, Union


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def cost(self, price_in_per_mtok: float, price_out_per_mtok: float) -> float:
        return (
            self.input_tokens * price_in_per_mtok + self.output_tokens * price_out_per_mtok
        ) / 1_000_000


class LLM(Protocol):
    usage: Usage

    def complete(self, step: str, system: str, user: str) -> str: ...


def _langfuse_callbacks() -> list:
    """Turn on Langfuse tracing when its keys are present. Otherwise do nothing."""
    if not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")):
        return []
    try:
        from langfuse.langchain import CallbackHandler  # langfuse v3
    except ImportError:
        try:
            from langfuse.callback import CallbackHandler  # langfuse v2
        except ImportError:
            return []
    return [CallbackHandler()]


class ChatLLM:
    def __init__(self, model: str):
        if not model:
            raise ValueError(
                "No model set. Put AGENT_MODEL in your .env, "
                'for example AGENT_MODEL="anthropic:<model name>".'
            )
        from langchain.chat_models import init_chat_model

        self._model = init_chat_model(model, temperature=0)
        self._callbacks = _langfuse_callbacks()
        self.usage = Usage()

    def complete(self, step: str, system: str, user: str) -> str:
        response = self._model.invoke(
            [("system", system), ("user", user)],
            config={"callbacks": self._callbacks, "run_name": step, "tags": [step]},
        )
        meta = getattr(response, "usage_metadata", None) or {}
        self.usage.calls += 1
        self.usage.input_tokens += int(meta.get("input_tokens", 0))
        self.usage.output_tokens += int(meta.get("output_tokens", 0))
        content = response.content
        if isinstance(content, list):  # some providers return content blocks
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
        return content


Scripted = Union[str, Callable[[str, str], str]]


class FakeLLM:
    """Scripted model for tests. No network, no cost.

    `script` maps a step name to a list of replies. Each call to that step
    takes the next reply. The last reply repeats if the list runs out.
    A reply can also be a function of (system, user).
    """

    def __init__(self, script: Dict[str, List[Scripted]], tokens_per_call: int = 100):
        self._script = {step: list(replies) for step, replies in script.items()}
        self._tokens_per_call = tokens_per_call
        self.usage = Usage()
        self.calls: List[Dict[str, str]] = []

    def complete(self, step: str, system: str, user: str) -> str:
        self.calls.append({"step": step, "system": system, "user": user})
        self.usage.calls += 1
        self.usage.input_tokens += self._tokens_per_call
        self.usage.output_tokens += self._tokens_per_call
        replies = self._script[step]
        reply = replies.pop(0) if len(replies) > 1 else replies[0]
        return reply(system, user) if callable(reply) else reply


class ModelOutputError(ValueError):
    pass


def extract_json(text: str) -> Any:
    """Pull one JSON value out of a model reply.

    Models often wrap JSON in a code fence or add a sentence before it.
    """
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    candidates = [fenced.group(1)] if fenced else []
    candidates.append(text)
    for candidate in candidates:
        candidate = candidate.strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        start = min((i for i in (candidate.find("{"), candidate.find("[")) if i != -1), default=-1)
        end = max(candidate.rfind("}"), candidate.rfind("]"))
        if start != -1 and end > start:
            try:
                return json.loads(candidate[start : end + 1])
            except json.JSONDecodeError:
                pass
    raise ModelOutputError("Model reply did not contain valid JSON")
