"""Central runtime configuration, loaded once from environment variables.

Every knob a deployer needs to touch without editing code lives here. Nothing
in the rest of the app reads `os.environ` directly -- that keeps the "what
can I configure" question answerable by reading one file instead of grepping
the whole tree.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- LLM provider -----------------------------------------------------
    # "mock" is the default so the app runs (and CI passes) with zero API
    # keys configured. Set to "openai" or "anthropic" for real inference.
    llm_provider: str = "mock"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    # --- Signal detection ---------------------------------------------------
    # Confidence is approximated by self-consistency: how many of N sampled
    # LLM calls agree on the same label set. See docs/adr/0002-confidence-via-self-consistency.md
    # for why this is a deliberate, documented simplification rather than
    # true probabilistic calibration.
    signal_self_consistency_samples: int = 3

    # --- RAG -----------------------------------------------------------------
    kb_path: str = "kb"
    rag_top_k: int = 3

    # --- Guardrails ------------------------------------------------------
    guardrail_blocklist_path: str = "app/guardrails/blocklist.txt"

    # --- Context window --------------------------------------------------
    context_window_turns: int = 12

    # --- Observability -----------------------------------------------------
    log_level: str = "INFO"
    metrics_enabled: bool = True


settings = Settings()
