import os
from dataclasses import dataclass, field


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def _float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


@dataclass
class Settings:
    # Any model string that langchain's init_chat_model understands,
    # for example "anthropic:<model name>" or "openai:<model name>".
    model: str = field(default_factory=lambda: os.environ.get("AGENT_MODEL", ""))
    max_attempts: int = field(default_factory=lambda: _int("AGENT_MAX_ATTEMPTS", 3))
    # Hard stop for one ticket. Input and output tokens added together.
    max_tokens_per_ticket: int = field(
        default_factory=lambda: _int("AGENT_MAX_TOKENS_PER_TICKET", 300_000)
    )
    max_files_read: int = field(default_factory=lambda: _int("AGENT_MAX_FILES_READ", 12))
    max_files_changed: int = field(default_factory=lambda: _int("AGENT_MAX_FILES_CHANGED", 10))
    max_file_bytes: int = field(default_factory=lambda: _int("AGENT_MAX_FILE_BYTES", 100_000))
    test_timeout_seconds: int = field(default_factory=lambda: _int("AGENT_TEST_TIMEOUT", 180))
    auto_approve: bool = False
    # Prices are optional. Set them to see a cost number in run records.
    # They are in USD per one million tokens.
    price_in_per_mtok: float = field(default_factory=lambda: _float("AGENT_PRICE_IN", 0.0))
    price_out_per_mtok: float = field(default_factory=lambda: _float("AGENT_PRICE_OUT", 0.0))
