"""OpenRouter chat-completions wrapper (OpenAI-compatible)."""
import os

from openai import OpenAI

_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is missing. Put it in .env")
        _client = OpenAI(
            base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=api_key,
            timeout=int(os.environ.get("LLM_TIMEOUT", "90")),
        )
    return _client


def get_model():
    return os.environ.get("MODEL_NAME", "nvidia/nemotron-3-ultra-550b-a55b:free")


def chat(messages, tools=None, temperature=0.2, max_tokens=None):
    """One LLM call. Returns the assistant message object."""
    if max_tokens is None:
        try:
            max_tokens = int(os.environ.get("MAX_TOKENS", "1200"))
        except ValueError:
            max_tokens = 1200
    kwargs = dict(
        model=get_model(),
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if tools:
        kwargs["tools"] = tools
    return get_client().chat.completions.create(**kwargs).choices[0].message
