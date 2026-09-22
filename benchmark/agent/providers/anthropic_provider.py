"""
anthropic_provider.py — Anthropic Claude API Provider Adapter.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple
import urllib.request
import urllib.error

from benchmark.agent.providers.base_provider import (
    AgentProvider,
    ProviderResponse,
    ProviderTokenUsage,
    ToolCallRequest,
)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

# Official pricing per 1M tokens: (input, output, cache_read, cache_write)
CLAUDE_PRICING: Dict[str, Tuple[float, float, float, float]] = {
    "claude-3-5-sonnet-20241022": (3.00, 15.00, 0.30, 3.75),
    "claude-3-5-sonnet-latest": (3.00, 15.00, 0.30, 3.75),
    "claude-3-7-sonnet-20250219": (3.00, 15.00, 0.30, 3.75),
    "claude-3-5-haiku-20241022": (0.80, 4.00, 0.08, 1.00),
    "default": (3.00, 15.00, 0.30, 3.75),
}


class AnthropicProvider(AgentProvider):
    """Direct HTTP client for Anthropic Messages API."""

    def __init__(
        self,
        model_name: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        temperature: float = 0.0,
        **kwargs: Any,
    ):
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        super().__init__(
            model_name=model_name,
            api_key=key,
            base_url=base_url or ANTHROPIC_API_URL,
            timeout=timeout,
            temperature=temperature,
            **kwargs,
        )

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def calculate_cost_usd(self, usage: ProviderTokenUsage) -> float:
        pricing = CLAUDE_PRICING.get(self.model_name, CLAUDE_PRICING["default"])
        in_price, out_price, cache_read_price, _ = pricing
        reg_in = max(0, usage.input_tokens - usage.cached_tokens)
        cost = (
            (reg_in / 1_000_000.0) * in_price
            + (usage.cached_tokens / 1_000_000.0) * cache_read_price
            + (usage.output_tokens / 1_000_000.0) * out_price
        )
        return round(cost, 6)

    def health_check(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "ANTHROPIC_API_KEY environment variable is not set"
        try:
            resp = self.send_turn(
                messages=[{"role": "user", "content": "ping"}],
                system_prompt="respond with 'pong'",
            )
            return True, f"Connected to {resp.actual_model} (request_id: {resp.request_id})"
        except Exception as e:
            return False, f"Anthropic connection failed: {e}"

    def send_turn(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> ProviderResponse:
        if not self.api_key:
            raise ConnectionError(
                "Cannot call Anthropic API: ANTHROPIC_API_KEY is not set. "
                "The benchmark fails closed when credentials are missing."
            )

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        }

        # Convert tools to Anthropic format
        anthropic_tools = []
        if tools:
            for t in tools:
                if t.get("type") == "function":
                    fn = t["function"]
                    anthropic_tools.append({
                        "name": fn["name"],
                        "description": fn.get("description", ""),
                        "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
                    })
                else:
                    anthropic_tools.append(t)

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": 4096,
            "temperature": self.temperature,
            "messages": messages,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if anthropic_tools:
            payload["tools"] = anthropic_tools

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.base_url, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic API error HTTP {err.code}: {err_body}") from err
        except Exception as err:
            raise ConnectionError(f"Anthropic network error: {err}") from err

        # Parse usage
        raw_usage = resp_data.get("usage", {})
        in_tok = raw_usage.get("input_tokens", 0)
        out_tok = raw_usage.get("output_tokens", 0)
        cache_read = raw_usage.get("cache_read_input_tokens", 0)
        cache_create = raw_usage.get("cache_creation_input_tokens", 0)
        usage = ProviderTokenUsage(
            input_tokens=in_tok + cache_create,
            output_tokens=out_tok,
            cached_tokens=cache_read,
            total_tokens=in_tok + out_tok + cache_create,
            raw_metadata=raw_usage,
        )

        # Parse content and tool calls
        content_parts: List[str] = []
        tool_calls: List[ToolCallRequest] = []
        for block in resp_data.get("content", []):
            b_type = block.get("type")
            if b_type == "text":
                content_parts.append(block.get("text", ""))
            elif b_type == "tool_use":
                tool_calls.append(ToolCallRequest(
                    id=block.get("id", f"call_{len(tool_calls)+1}"),
                    name=block.get("name", ""),
                    arguments=block.get("input", {}),
                ))

        actual_model = resp_data.get("model", self.model_name)
        req_id = resp_data.get("id")
        finish_reason = resp_data.get("stop_reason", "end_turn")
        cost = self.calculate_cost_usd(usage)

        return ProviderResponse(
            provider="anthropic",
            requested_model=self.model_name,
            actual_model=actual_model,
            request_id=req_id,
            finish_reason=finish_reason,
            content="\n".join(content_parts) if content_parts else None,
            tool_calls=tool_calls,
            usage=usage,
            cost_usd=cost,
            raw_response=self._sanitize_dict(resp_data),
        )
