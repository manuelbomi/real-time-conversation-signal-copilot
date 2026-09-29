"""Rolling per-session conversation context.

Short utterances ("yeah, maybe", "how much?") are ambiguous in isolation --
the signal detector and recommendation engine both need a few turns of
prior context to interpret them correctly. `ConversationContext` is a
bounded deque per session: bounded because an unbounded transcript would
(a) make every LLM call slower and more expensive as a call runs long, and
(b) eventually exceed the model's context window. `context_window_turns`
(default 12) is a deliberately small, configurable trade-off between
disambiguation quality and latency/cost -- see docs/PRODUCTION.md.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Turn:
    speaker: str
    text: str
    ts: float


@dataclass
class ConversationContext:
    max_turns: int = 12
    _turns: deque[Turn] = field(default_factory=deque)

    def __post_init__(self) -> None:
        self._turns = deque(self._turns, maxlen=self.max_turns)

    def add(self, turn: Turn) -> None:
        self._turns.append(turn)

    def as_prompt_text(self) -> str:
        """Render prior turns (excluding the very latest, which callers
        pass separately as the utterance being classified) as
        `speaker: text` lines, oldest first.
        """
        prior = list(self._turns)[:-1] if self._turns else []
        return "\n".join(f"{t.speaker}: {t.text}" for t in prior)

    def __len__(self) -> int:
        return len(self._turns)
