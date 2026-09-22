"""
test_providers.py — Unit tests for LLM provider adapters and fail-closed security.
"""
import pytest

from benchmark.agent.providers.base_provider import ProviderTokenUsage
from benchmark.agent.providers.factory import get_provider
from benchmark.agent.providers.anthropic_provider import AnthropicProvider
from benchmark.agent.providers.openai_provider import OpenAIProvider
from benchmark.agent.providers.gemini_provider import GeminiProvider


def test_provider_factory_resolution():
    p_claude = get_provider(model_name="claude-3-5-sonnet-20241022", api_key="dummy")
    assert isinstance(p_claude, AnthropicProvider)
    assert p_claude.provider_name == "anthropic"

    p_gpt = get_provider(model_name="gpt-4o", api_key="dummy")
    assert isinstance(p_gpt, OpenAIProvider)
    assert p_gpt.provider_name == "openai"

    p_gemini = get_provider(model_name="gemini-2.0-flash", api_key="dummy")
    assert isinstance(p_gemini, GeminiProvider)
    assert p_gemini.provider_name == "gemini"


def test_provider_fail_closed_without_credentials():
    p_claude = AnthropicProvider(api_key=None)
    p_claude.api_key = None  # Ensure empty

    healthy, msg = p_claude.health_check()
    assert healthy is False
    assert "not set" in msg.lower()

    # Sending turn without credentials raises ConnectionError
    with pytest.raises(ConnectionError, match="Cannot call Anthropic API"):
        p_claude.send_turn([{"role": "user", "content": "hello"}])


def test_secret_sanitization():
    p = AnthropicProvider(api_key="sk-ant-test123456789")
    dirty = {
        "model": "claude-3-5-sonnet",
        "api_key": "sk-ant-test123456789",
        "auth_token": "secret_abc",
        "nested": {"bearer_token": "top_secret", "normal_field": 42},
    }
    clean = p._sanitize_dict(dirty)
    assert clean["api_key"] == "[REDACTED]"
    assert clean["auth_token"] == "[REDACTED]"
    assert clean["nested"]["bearer_token"] == "[REDACTED]"
    assert clean["nested"]["normal_field"] == 42


def test_anthropic_cost_calculation():
    p = AnthropicProvider(model_name="claude-3-5-sonnet-20241022", api_key="dummy")
    # 1,000,000 input tokens (500k cached @ $0.30/M, 500k regular @ $3.00/M) + 100k output @ $15.00/M
    usage = ProviderTokenUsage(input_tokens=1_000_000, output_tokens=100_000, cached_tokens=500_000)
    cost = p.calculate_cost_usd(usage)
    # (0.5 * 3.0) + (0.5 * 0.3) + (0.1 * 15.0) = 1.50 + 0.15 + 1.50 = 3.15
    assert pytest.approx(cost, 0.001) == 3.15
