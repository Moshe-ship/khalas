"""Arabic prompt optimization engine."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .providers import LLMResponse, call_llm


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class ComparisonResult:
    """Side-by-side Arabic vs English prompt comparison."""

    arabic_response: LLMResponse
    english_response: LLMResponse
    token_ratio: float = 0.0   # ar / en  (>1 means Arabic uses more tokens)
    cost_ratio: float = 0.0
    latency_ratio: float = 0.0
    quality_delta: str = ""    # human-readable quality note


@dataclass
class OptimizationResult:
    """Result of applying a single optimization technique."""

    original_prompt: str
    optimized_prompt: str
    original_response: LLMResponse
    optimized_response: LLMResponse
    token_savings_pct: float = 0.0
    cost_savings_pct: float = 0.0
    technique_used: str = ""


# ---------------------------------------------------------------------------
# Optimization techniques -- each rewrites an Arabic prompt
# ---------------------------------------------------------------------------


def technique_add_language_hint(prompt: str) -> str:
    """Prepend an explicit MSA instruction to guide the model."""
    prefix = "\u0623\u062c\u0628 \u0628\u0627\u0644\u0644\u063a\u0629 \u0627\u0644\u0639\u0631\u0628\u064a\u0629 \u0627\u0644\u0641\u0635\u062d\u0649:"
    return f"{prefix} {prompt}"


def technique_simplify_arabic(prompt: str) -> str:
    """Replace verbose MSA constructions with shorter equivalents.

    This is a rule-based pass -- it targets common redundancies found in
    Arabic prompts without changing meaning.
    """
    replacements: list[tuple[str, str]] = [
        # "from the possible that" -> "can"
        ("\u0645\u0646 \u0627\u0644\u0645\u0645\u0643\u0646 \u0623\u0646", "\u064a\u0645\u0643\u0646"),
        # "do the work of" -> "do"
        ("\u0642\u0645 \u0628\u0639\u0645\u0644", "\u0627\u0639\u0645\u0644"),
        # "give me information about" -> "what is"
        ("\u0623\u0639\u0637\u0646\u064a \u0645\u0639\u0644\u0648\u0645\u0627\u062a \u0639\u0646", "\u0645\u0627 \u0647\u0648"),
        # "I would like that" -> "I want"
        ("\u0623\u0648\u062f \u0623\u0646", "\u0623\u0631\u064a\u062f"),
        # "please" (verbose form)
        ("\u0645\u0646 \u0641\u0636\u0644\u0643", ""),
        # "in a detailed manner" -> "detail"
        ("\u0628\u0634\u0643\u0644 \u0645\u0641\u0635\u0644", "\u0628\u0627\u0644\u062a\u0641\u0635\u064a\u0644"),
        # "with regard to" -> "about"
        ("\u0641\u064a\u0645\u0627 \u064a\u062a\u0639\u0644\u0642 \u0628\u0640", "\u0639\u0646"),
        # "that which" -> "what"
        ("\u0627\u0644\u0630\u064a \u064a\u062a\u0639\u0644\u0642 \u0628\u0640", "\u0639\u0646"),
    ]
    result = prompt
    for old, new in replacements:
        result = result.replace(old, new)
    # Collapse multiple spaces left by removals.
    result = re.sub(r"  +", " ", result).strip()
    return result


def technique_english_backbone(prompt: str) -> str:
    """Keep technical / Latin-script terms, wrap in Arabic framing.

    Identifies English words already present and restructures so the
    instruction layer is in Arabic while domain terms stay in English.
    """
    english_words = re.findall(r"[A-Za-z]{2,}", prompt)
    if not english_words:
        return prompt
    terms = ", ".join(dict.fromkeys(english_words))  # unique, order-preserved
    # "Explain the following technical terms in Arabic:"
    return (
        "\u0627\u0634\u0631\u062d \u0627\u0644\u0645\u0635\u0637\u0644\u062d\u0627\u062a "
        "\u0627\u0644\u062a\u0627\u0644\u064a\u0629 \u0628\u0627\u0644\u0639\u0631\u0628\u064a\u0629: "
        f"{terms}\n\n{prompt}"
    )


def technique_bilingual_instruction(prompt: str) -> str:
    """Give the instruction in English, ask for Arabic output."""
    return (
        f"Answer the following in Modern Standard Arabic.\n\n{prompt}"
    )


def technique_shorten(prompt: str) -> str:
    """Remove filler words and redundant connectors."""
    fillers: list[str] = [
        "\u0628\u0627\u0644\u0625\u0636\u0627\u0641\u0629 \u0625\u0644\u0649 \u0630\u0644\u0643",  # in addition to that
        "\u0639\u0644\u0649 \u0633\u0628\u064a\u0644 \u0627\u0644\u0645\u062b\u0627\u0644",          # for example
        "\u0643\u0645\u0627 \u0647\u0648 \u0645\u0639\u0631\u0648\u0641",                              # as is known
        "\u0641\u064a \u0627\u0644\u0648\u0627\u0642\u0639",                                            # in reality
        "\u0628\u0634\u0643\u0644 \u0639\u0627\u0645",                                                  # in general
        "\u0645\u0646 \u0627\u0644\u0645\u0639\u0631\u0648\u0641 \u0623\u0646",                        # it is known that
        "\u064a\u062c\u0628 \u0627\u0644\u0625\u0634\u0627\u0631\u0629 \u0625\u0644\u0649 \u0623\u0646",  # it should be noted that
    ]
    result = prompt
    for filler in fillers:
        result = result.replace(filler, "")
    result = re.sub(r"  +", " ", result).strip()
    return result


# ---------------------------------------------------------------------------
# New techniques (from research: LLMLingua, AraToken, prompt compression)
# ---------------------------------------------------------------------------


def technique_normalize_arabic(prompt: str) -> str:
    """Normalize Arabic text to reduce token fragmentation.
    Based on AraToken research — normalizing alef/ya/tashkeel reduces tokenized length."""
    # Strip tashkeel (diacritics)
    prompt = re.sub("[\u064B-\u065F\u0670]", "", prompt)
    # Normalize alef forms: أ إ آ → ا
    prompt = re.sub("[\u0623\u0625\u0622]", "\u0627", prompt)
    # Normalize ya: ى → ي
    prompt = prompt.replace("\u0649", "\u064A")
    # Remove tatweel
    prompt = prompt.replace("\u0640", "")
    return prompt


def technique_strip_fewshot(prompt: str) -> str:
    """Remove few-shot examples from prompt — use zero-shot instead.
    Research shows zero-shot is nearly as effective for Arabic while cutting tokens significantly."""
    # Remove common few-shot patterns: "مثال:", "Example:", numbered examples
    patterns = [
        r"(?:مثال|مثال \d+|Example \d*)\s*:.*?(?=(?:مثال|Example|\Z))",
        r"الإدخال\s*:.*?الإخراج\s*:.*?(?=\n\n|\Z)",
        r"Input\s*:.*?Output\s*:.*?(?=\n\n|\Z)",
    ]
    result = prompt
    for pat in patterns:
        result = re.sub(pat, "", result, flags=re.DOTALL)
    return re.sub(r"\n{3,}", "\n\n", result).strip()


def technique_system_prompt_split(prompt: str) -> str:
    """Move static instructions to a reusable prefix, keep only the variable query.
    This simulates what you'd put in a system prompt (cached/reused, not re-tokenized)."""
    # Extract the last sentence/question as the core query
    lines = [l.strip() for l in prompt.split("\n") if l.strip()]
    if len(lines) <= 1:
        return prompt
    # Assume last line is the actual question, rest is instruction
    return f"[System: {' '.join(lines[:-1])}]\n{lines[-1]}"


def technique_transliterate(prompt: str) -> str:
    """Convert Arabic to rough Arabizi (transliterated Latin) for token reduction.
    Some models tokenize Latin text much more efficiently. Use as cost baseline."""
    mapping = {
        "ا": "a", "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "h",
        "خ": "kh", "د": "d", "ذ": "th", "ر": "r", "ز": "z", "س": "s",
        "ش": "sh", "ص": "s", "ض": "d", "ط": "t", "ظ": "z", "ع": "3",
        "غ": "gh", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m",
        "ن": "n", "ه": "h", "و": "w", "ي": "y", "ة": "a", "ى": "a",
        "أ": "a", "إ": "e", "آ": "a", "ء": "'", "ؤ": "'", "ئ": "'",
    }
    result = []
    for c in prompt:
        if c in mapping:
            result.append(mapping[c])
        else:
            result.append(c)
    return "".join(result)


def technique_compress_connectors(prompt: str) -> str:
    """Aggressively compress Arabic connectors and prepositions.
    Based on LLMLingua-style selective compression — remove low-information tokens."""
    # Common low-info connectors in Arabic prompts
    removals = [
        "وذلك", "حيث أن", "ومن ثم", "وعليه", "لذلك",
        "بالتالي", "وبالتالي", "علاوة على ذلك", "فضلاً عن",
        "من جهة أخرى", "في هذا السياق", "مما يعني",
        "الأمر الذي", "نظراً ل", "وفي ضوء ذلك",
        "ينبغي الإشارة إلى", "تجدر الإشارة إلى",
        "من الجدير بالذكر", "لا بد من الإشارة",
    ]
    result = prompt
    for r in removals:
        result = result.replace(r, "")
    result = re.sub(r"  +", " ", result).strip()
    return result


# All techniques, in order of expected impact.
TECHNIQUES: list[tuple[str, callable]] = [
    ("normalize_arabic", technique_normalize_arabic),
    ("compress_connectors", technique_compress_connectors),
    ("shorten", technique_shorten),
    ("simplify_arabic", technique_simplify_arabic),
    ("strip_fewshot", technique_strip_fewshot),
    ("system_prompt_split", technique_system_prompt_split),
    ("add_language_hint", technique_add_language_hint),
    ("bilingual_instruction", technique_bilingual_instruction),
    ("english_backbone", technique_english_backbone),
    ("transliterate", technique_transliterate),
]


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def compare_languages(
    prompt_ar: str,
    prompt_en: str,
    provider: str,
    model: str | None = None,
    api_key: str | None = None,
) -> ComparisonResult:
    """Send the same prompt in Arabic and English, compare tokens/cost/latency."""
    ar = call_llm(provider, prompt_ar, model=model, api_key=api_key)
    en = call_llm(provider, prompt_en, model=model, api_key=api_key)

    en_total = en.input_tokens + en.output_tokens
    ar_total = ar.input_tokens + ar.output_tokens

    token_ratio = ar_total / en_total if en_total else 0.0
    cost_ratio = ar.cost / en.cost if en.cost else 0.0
    latency_ratio = ar.latency_ms / en.latency_ms if en.latency_ms else 0.0

    # Build a simple quality note.
    if ar.error or en.error:
        quality = f"errors: ar={ar.error}, en={en.error}"
    elif token_ratio > 1.3:
        quality = f"Arabic uses {token_ratio:.1f}x more tokens than English"
    elif token_ratio < 0.9:
        quality = "Arabic is more token-efficient than English here"
    else:
        quality = "Token usage is roughly equal"

    return ComparisonResult(
        arabic_response=ar,
        english_response=en,
        token_ratio=round(token_ratio, 3),
        cost_ratio=round(cost_ratio, 3),
        latency_ratio=round(latency_ratio, 3),
        quality_delta=quality,
    )


def optimize_prompt(
    prompt: str,
    provider: str,
    model: str | None = None,
    api_key: str | None = None,
    techniques: list[str] | None = None,
) -> list[OptimizationResult]:
    """Try each technique on *prompt*, return results sorted by savings.

    If *techniques* is given, only those named techniques are tried.
    """
    # Baseline: run the original prompt once.
    original_resp = call_llm(provider, prompt, model=model, api_key=api_key)
    original_tokens = original_resp.input_tokens + original_resp.output_tokens

    results: list[OptimizationResult] = []

    for name, func in TECHNIQUES:
        if techniques and name not in techniques:
            continue

        optimized = func(prompt)
        if optimized == prompt:
            continue  # technique had no effect

        opt_resp = call_llm(provider, optimized, model=model, api_key=api_key)
        opt_tokens = opt_resp.input_tokens + opt_resp.output_tokens

        token_savings = (
            ((original_tokens - opt_tokens) / original_tokens * 100)
            if original_tokens
            else 0.0
        )
        cost_savings = (
            ((original_resp.cost - opt_resp.cost) / original_resp.cost * 100)
            if original_resp.cost
            else 0.0
        )

        results.append(
            OptimizationResult(
                original_prompt=prompt,
                optimized_prompt=optimized,
                original_response=original_resp,
                optimized_response=opt_resp,
                token_savings_pct=round(token_savings, 1),
                cost_savings_pct=round(cost_savings, 1),
                technique_used=name,
            )
        )

    # Best savings first.
    results.sort(key=lambda r: r.token_savings_pct, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Projection helpers
# ---------------------------------------------------------------------------


def estimate_monthly_savings(
    comparison: ComparisonResult,
    volume_m: float,
) -> dict:
    """Project monthly savings if Arabic prompts were optimized to English-level.

    *volume_m* is the number of requests per month (in millions).

    Returns a dict with keys: volume_m, ar_cost_m, en_cost_m, savings_m, savings_pct.
    """
    ar = comparison.arabic_response
    en = comparison.english_response

    ar_cost_per_req = ar.cost if ar.cost else 0.0
    en_cost_per_req = en.cost if en.cost else 0.0

    total_requests = volume_m * 1_000_000
    ar_cost_m = ar_cost_per_req * total_requests
    en_cost_m = en_cost_per_req * total_requests
    savings_m = ar_cost_m - en_cost_m
    savings_pct = (savings_m / ar_cost_m * 100) if ar_cost_m else 0.0

    return {
        "volume_m": volume_m,
        "ar_cost_m": round(ar_cost_m, 2),
        "en_cost_m": round(en_cost_m, 2),
        "savings_m": round(savings_m, 2),
        "savings_pct": round(savings_pct, 1),
    }
