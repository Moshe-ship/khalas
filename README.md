# khalas (خلص) — Arabic Prompt Optimizer

> artok shows you pay more. arabench shows you get less. khalas fixes it.

## Why

Same prompt costs 2-5x more in Arabic. Tokenizers fragment Arabic characters into byte sequences, inflating token counts and API bills.

**khalas** compares Arabic vs English side by side, then optimizes the Arabic prompt to use fewer tokens without losing quality.

## Install

```bash
pip install khalas
```

## Quick Start

```bash
khalas compare "الذكاء الاصطناعي يغير العالم" "AI is changing the world" --provider openai
```

## Commands

| Command | Description |
|---------|-------------|
| `compare` | Side-by-side AR vs EN token count and cost |
| `optimize` | Rewrite Arabic prompt to reduce tokens |
| `savings` | Show how much you save after optimization |
| `explain` | Break down where tokens are wasted |
| `config` | Set default provider and API keys |

## Optimization Techniques

| Technique | What it does |
|-----------|--------------|
| **Language Hint** | Prepend language context to guide tokenizer |
| **Simplify** | Replace complex Arabic structures with simpler equivalents |
| **English Backbone** | Keep instructions in English, content in Arabic |
| **Bilingual Instruction** | Mix EN structure with AR key terms |
| **Shorten** | Remove filler words and redundancy |

## Supported Providers

| Provider | Model (March 2026) |
|----------|-------------------|
| OpenAI | gpt-5.4 |
| Anthropic | claude-opus-4-6 |
| Google | gemini-3.1-pro |
| DeepSeek | deepseek-v3.2 |
| Mistral | mistral-large-3 |
| Groq | groq-llama-4 |
| Qwen | qwen-3.5 |
| xAI | grok-2 |

---

<p dir="rtl">مقدمة من <a href="https://x.com/i/communities/2032184341682643429">مجتمع الذكاء الاصطناعي السعودي</a> للعرب أولا وللعالم أجمع</p>

Brought to you by the [Saudi AI Community](https://x.com/i/communities/2032184341682643429) — for Arabs first, and the world at large.

## The Series

- [artok](https://github.com/Moshe-ship/artok) — Arabic Token Tax Calculator
- [bidi-guard](https://github.com/Moshe-ship/bidi-guard) — Trojan Source Attack Scanner
- [arabench](https://github.com/Moshe-ship/arabench) — Arabic LLM Benchmark
- [majal](https://github.com/Moshe-ship/majal) — Arabic AI Tools Hub
- [khalas](https://github.com/Moshe-ship/khalas) — Arabic Prompt Optimizer

## License

MIT — [Musa the Carpenter](https://github.com/Moshe-ship)
