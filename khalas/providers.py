"""LLM provider interface for khalas."""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from .config import get_api_key


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class Provider:
    name: str
    display_name: str
    default_model: str
    cost_input: float   # per 1M input tokens
    cost_output: float  # per 1M output tokens
    api_base: str


@dataclass
class LLMResponse:
    text: str = ""
    model: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost: float = 0.0
    error: str | None = None


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

PROVIDERS: list[Provider] = [
    Provider(
        name="openai",
        display_name="OpenAI",
        default_model="gpt-5.4",
        cost_input=2.50,
        cost_output=10.00,
        api_base="https://api.openai.com/v1",
    ),
    Provider(
        name="anthropic",
        display_name="Anthropic",
        default_model="claude-opus-4-6",
        cost_input=5.00,
        cost_output=25.00,
        api_base="https://api.anthropic.com",
    ),
    Provider(
        name="google",
        display_name="Google",
        default_model="gemini-3.1-pro-preview",
        cost_input=2.00,
        cost_output=12.00,
        api_base="https://generativelanguage.googleapis.com",
    ),
    Provider(
        name="deepseek",
        display_name="DeepSeek",
        default_model="deepseek-chat",
        cost_input=0.27,
        cost_output=1.10,
        api_base="https://api.deepseek.com/v1",
    ),
    Provider(
        name="mistral",
        display_name="Mistral",
        default_model="mistral-large-latest",
        cost_input=0.50,
        cost_output=1.50,
        api_base="https://api.mistral.ai/v1",
    ),
    Provider(
        name="groq",
        display_name="Groq",
        default_model="llama-3.3-70b-versatile",
        cost_input=0.18,
        cost_output=0.18,
        api_base="https://api.groq.com/openai/v1",
    ),
    Provider(
        name="qwen",
        display_name="Qwen",
        default_model="qwen3.5-plus",
        cost_input=0.26,
        cost_output=1.56,
        api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    ),
    Provider(
        name="xai",
        display_name="xAI",
        default_model="grok-4-1-fast",
        cost_input=3.00,
        cost_output=15.00,
        api_base="https://api.x.ai/v1",
    ),
]


def get_provider(name: str) -> Provider | None:
    """Look up a provider by name."""
    for p in PROVIDERS:
        if p.name == name:
            return p
    return None


def get_available_providers() -> list[Provider]:
    """Return only providers that have an API key configured."""
    return [p for p in PROVIDERS if get_api_key(p.name)]


# ---------------------------------------------------------------------------
# Cost calculation
# ---------------------------------------------------------------------------


def calculate_cost(
    provider: Provider,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Calculate cost in USD from token counts and provider pricing."""
    return (
        (input_tokens / 1_000_000) * provider.cost_input
        + (output_tokens / 1_000_000) * provider.cost_output
    )


# ---------------------------------------------------------------------------
# Internal call helpers -- one per API shape
# ---------------------------------------------------------------------------


def _call_openai_compatible(
    provider: Provider,
    prompt: str,
    system: str | None,
    api_key: str,
    model: str,
    timeout: float,
) -> LLMResponse:
    """OpenAI-compatible: openai, deepseek, mistral, groq, qwen, xai."""
    url = f"{provider.api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
    }

    t0 = time.monotonic()
    resp = httpx.post(url, json=payload, headers=headers, timeout=timeout)
    latency = (time.monotonic() - t0) * 1000

    data = resp.json()
    if resp.status_code != 200:
        return LLMResponse(
            provider=provider.name,
            model=model,
            latency_ms=latency,
            error=data.get("error", {}).get("message", resp.text),
        )

    usage = data.get("usage", {})
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    return LLMResponse(
        text=data["choices"][0]["message"]["content"],
        model=data.get("model", model),
        provider=provider.name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency,
        cost=calculate_cost(provider, input_tokens, output_tokens),
    )


def _call_anthropic(
    provider: Provider,
    prompt: str,
    system: str | None,
    api_key: str,
    model: str,
    timeout: float,
) -> LLMResponse:
    """Anthropic Messages API."""
    url = f"{provider.api_base}/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload: dict = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        payload["system"] = system

    t0 = time.monotonic()
    resp = httpx.post(url, json=payload, headers=headers, timeout=timeout)
    latency = (time.monotonic() - t0) * 1000

    data = resp.json()
    if resp.status_code != 200:
        return LLMResponse(
            provider=provider.name,
            model=model,
            latency_ms=latency,
            error=data.get("error", {}).get("message", resp.text),
        )

    usage = data.get("usage", {})
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    return LLMResponse(
        text="".join(text_blocks),
        model=data.get("model", model),
        provider=provider.name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency,
        cost=calculate_cost(provider, input_tokens, output_tokens),
    )


def _call_google(
    provider: Provider,
    prompt: str,
    system: str | None,
    api_key: str,
    model: str,
    timeout: float,
) -> LLMResponse:
    """Google Gemini generateContent API."""
    url = (
        f"{provider.api_base}/v1beta/models/{model}:generateContent"
        f"?key={api_key}"
    )
    headers = {"Content-Type": "application/json"}

    contents: list[dict] = [
        {"role": "user", "parts": [{"text": prompt}]},
    ]
    payload: dict = {"contents": contents}
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}

    t0 = time.monotonic()
    resp = httpx.post(url, json=payload, headers=headers, timeout=timeout)
    latency = (time.monotonic() - t0) * 1000

    data = resp.json()
    if resp.status_code != 200:
        err = data.get("error", {})
        err_msg = err.get("message", resp.text)
        if api_key and api_key in err_msg:
            err_msg = err_msg.replace(api_key, "***")
        return LLMResponse(
            provider=provider.name,
            model=model,
            latency_ms=latency,
            error=err_msg,
        )

    candidates = data.get("candidates", [])
    text = ""
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)

    usage = data.get("usageMetadata", {})
    input_tokens = usage.get("promptTokenCount", 0)
    output_tokens = usage.get("candidatesTokenCount", 0)
    return LLMResponse(
        text=text,
        model=model,
        provider=provider.name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency,
        cost=calculate_cost(provider, input_tokens, output_tokens),
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def call_llm(
    provider_name: str,
    prompt: str,
    system: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    timeout: float = 60.0,
) -> LLMResponse:
    """Call any supported LLM provider.

    Never raises -- errors go in ``LLMResponse.error``.
    """
    provider = get_provider(provider_name)
    if provider is None:
        return LLMResponse(error=f"Unknown provider: {provider_name}")

    key = api_key or get_api_key(provider_name)
    if not key:
        return LLMResponse(
            provider=provider_name,
            error=f"No API key for {provider_name}",
        )

    resolved_model = model or provider.default_model

    try:
        if provider_name in (
            "openai", "deepseek", "mistral", "groq", "qwen", "xai",
        ):
            return _call_openai_compatible(
                provider, prompt, system, key, resolved_model, timeout,
            )
        if provider_name == "anthropic":
            return _call_anthropic(
                provider, prompt, system, key, resolved_model, timeout,
            )
        if provider_name == "google":
            return _call_google(
                provider, prompt, system, key, resolved_model, timeout,
            )
        return LLMResponse(
            provider=provider_name,
            error=f"No call handler for provider: {provider_name}",
        )
    except httpx.TimeoutException:
        return LLMResponse(
            provider=provider_name,
            model=resolved_model,
            error=f"Request timed out after {timeout}s",
        )
    except Exception as exc:
        err_msg = str(exc)
        if key and key in err_msg:
            err_msg = err_msg.replace(key, "***")
        return LLMResponse(
            provider=provider_name,
            model=resolved_model,
            error=err_msg,
        )
