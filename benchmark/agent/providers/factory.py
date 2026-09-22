"""
factory.py — Provider Resolution and Factory.
"""
from __future__ import annotations

from typing import Any, Optional

from benchmark.agent.providers.anthropic_provider import AnthropicProvider
from benchmark.agent.providers.base_provider import AgentProvider
from benchmark.agent.providers.gemini_provider import GeminiProvider
from benchmark.agent.providers.openai_provider import OpenAIProvider


def get_provider(
    provider_name: Optional[str] = None,
    model_name: str = "claude-3-5-sonnet-20241022",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs: Any,
) -> AgentProvider:
    """Instantiate and return the appropriate provider adapter."""
    p_name = (provider_name or "").lower()

    if not p_name:
        m_lower = model_name.lower()
        if "claude" in m_lower:
            p_name = "anthropic"
        elif "gemini" in m_lower:
            p_name = "gemini"
        elif "gpt" in m_lower or "o3" in m_lower:
            p_name = "openai"
        else:
            p_name = "openai"

    if p_name == "anthropic":
        return AnthropicProvider(model_name=model_name, api_key=api_key, base_url=base_url, **kwargs)
    elif p_name in ("openai", "ollama", "vllm", "litellm"):
        return OpenAIProvider(model_name=model_name, api_key=api_key, base_url=base_url, **kwargs)
    elif p_name == "gemini":
        return GeminiProvider(model_name=model_name, api_key=api_key, base_url=base_url, **kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {p_name}")
