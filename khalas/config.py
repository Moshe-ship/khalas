"""Configuration for khalas."""
from __future__ import annotations

import os


ENV_KEYS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "groq": "GROQ_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "xai": "XAI_API_KEY",
}


def get_api_key(provider: str) -> str | None:
    """Return the API key for *provider* from environment, or None."""
    env = ENV_KEYS.get(provider)
    return os.environ.get(env) if env else None


def list_configured() -> list[str]:
    """Return provider names that have an API key set."""
    return [p for p in ENV_KEYS if get_api_key(p)]
