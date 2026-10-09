"""Chat-completions wrapper with dual support: Google Gemini & OpenRouter."""
import logging
import os
import re

from openai import OpenAI

logger = logging.getLogger(__name__)

_client = None
_client_provider = None

FALLBACK_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3.5-lightning:free",
    "google/gemma-4-31b-it:free",
]


def get_client(provider=None):
    """Returns OpenAI-compatible client. Prefers Gemini if GEMINI_API_KEY is present."""
    global _client, _client_provider
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")

    target_provider = provider
    if not target_provider:
        target_provider = "gemini" if gemini_key else "openrouter"

    if _client is not None and _client_provider == target_provider:
        return _client

    timeout = int(os.environ.get("LLM_TIMEOUT", "45"))

    if target_provider == "gemini":
        if not gemini_key:
            raise RuntimeError("GEMINI_API_KEY is missing. Put it in .env or Render environment.")
        _client = OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=gemini_key,
            timeout=timeout,
        )
        _client_provider = "gemini"
    else:
        if not openrouter_key:
            raise RuntimeError("OPENROUTER_API_KEY is missing. Put it in .env")
        _client = OpenAI(
            base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=openrouter_key,
            timeout=timeout,
        )
        _client_provider = "openrouter"

    return _client


def get_model():
    gemini_key = os.environ.get("GEMINI_API_KEY")
    default_model = "gemini-3.8-flash" if gemini_key else "nvidia/nemotron-3-ultra-550b-a55b:free"
    return os.environ.get("MODEL_NAME", default_model)


def _strip_thinking(text):
    if not text:
        return text
    # Strip <think>...</think>
    text = re.sub(r"(?s)<think>.*?</think>", "", text).strip()
    # Strip "Here's a thinking process: ..." blocks
    text = re.sub(r"(?s)^Here'?s a thinking process:.*?\n\n(?=[A-Z0-9#*])", "", text).strip()
    # Strip numbered thinking trace blocks like "1.  **Analyze User Input:** ... "
    text = re.sub(r"(?s)^\d+\.\s+\*\*Analyze User Input:.*?\n\n(?=[A-Z#*])", "", text).strip()
    return text


def chat(messages, tools=None, temperature=0.2, max_tokens=None):
    """One LLM call with automated fallbacks across Gemini and OpenRouter."""
    if max_tokens is None:
        try:
            max_tokens = int(os.environ.get("MAX_TOKENS", "1200"))
        except ValueError:
            max_tokens = 1200

    primary_model = get_model()
    models_to_try = [primary_model]
    for m in FALLBACK_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    gemini_key = os.environ.get("GEMINI_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")

    last_err = None
    for model_name in models_to_try:
        # Determine provider based on model name
        is_gemini_model = "gemini" in model_name.lower()
        if is_gemini_model and not gemini_key:
            continue
        if not is_gemini_model and not openrouter_key:
            continue

        provider = "gemini" if is_gemini_model else "openrouter"
        client = get_client(provider)

        kwargs = dict(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if tools:
            kwargs["tools"] = tools

        try:
            resp = client.chat.completions.create(**kwargs)
            if resp and getattr(resp, "choices", None) and len(resp.choices) > 0:
                msg = resp.choices[0].message
                if getattr(msg, "content", None):
                    msg.content = _strip_thinking(msg.content)
                return msg
            err_info = getattr(resp, "error", None) or "Empty choices"
            logger.warning("Model %s (%s) failed: %s. Trying fallback...", model_name, provider, err_info)
            last_err = RuntimeError(f"Model {model_name} returned no choices: {err_info}")
        except Exception as exc:
            logger.warning("Model %s (%s) exception: %s. Trying fallback...", model_name, provider, exc)
            last_err = exc
            continue

    if last_err:
        raise last_err
    raise RuntimeError("All LLM models failed to respond.")

