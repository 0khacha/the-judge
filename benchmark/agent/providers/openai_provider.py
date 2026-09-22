"""
openai_provider.py — OpenAI & OpenAI-Compatible API Provider Adapter.

Supports:
  - Official OpenAI API (api.openai.com)
  - Local OpenAI-compatible servers (Ollama, LM Studio, vLLM, LiteLLM) via base_url
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

OPENAI_DEFAULT_URL = "https://api.openai.com/v1/chat/completions"

OPENAI_PRICING: Dict[str, Tuple[float, float, float]] = {
    "gpt-4o": (2.50, 10.00, 1.25),
    "gpt-4o-2024-11-20": (2.50, 10.00, 1.25),
    "gpt-4o-mini": (0.15, 0.60, 0.075),
    "o3-mini": (1.10, 4.40, 0.55),
    "default": (2.50, 10.00, 1.25),
}


class OpenAIProvider(AgentProvider):
    """Client for OpenAI Chat Completions API and compatible local endpoints."""

    def __init__(
        self,
        model_name: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        temperature: float = 0.0,
        **kwargs: Any,
    ):
        key = api_key or os.environ.get("OPENAI_API_KEY")
        url = base_url or os.environ.get("OPENAI_BASE_URL") or OPENAI_DEFAULT_URL
        if url.endswith("/v1") or url.endswith("/v1/"):
            url = url.rstrip("/") + "/chat/completions"
        super().__init__(
            model_name=model_name,
            api_key=key,
            base_url=url,
            timeout=timeout,
            temperature=temperature,
            **kwargs,
        )

    @property
    def provider_name(self) -> str:
        return "openai"

    def calculate_cost_usd(self, usage: ProviderTokenUsage) -> float:
        pricing = OPENAI_PRICING.get(self.model_name, OPENAI_PRICING["default"])
        in_price, out_price, cache_price = pricing
        reg_in = max(0, usage.input_tokens - usage.cached_tokens)
        cost = (
            (reg_in / 1_000_000.0) * in_price
            + (usage.cached_tokens / 1_000_000.0) * cache_price
            + (usage.output_tokens / 1_000_000.0) * out_price
        )
        return round(cost, 6)

    def health_check(self) -> Tuple[bool, str]:
        # For local endpoints (e.g. localhost), api_key may not be strictly required
        is_local = "localhost" in self.base_url or "127.0.0.1" in self.base_url
        if not self.api_key and not is_local:
            return False, "OPENAI_API_KEY is not set and base_url is not local"
        try:
            resp = self.send_turn(
                messages=[{"role": "user", "content": "ping"}],
                system_prompt="respond with 'pong'",
            )
            return True, f"Connected to {resp.actual_model} (request_id: {resp.request_id})"
        except Exception as e:
            return False, f"OpenAI connection failed: {e}"

    def send_turn(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> ProviderResponse:
        is_local = "localhost" in self.base_url or "127.0.0.1" in self.base_url
        if not self.api_key and not is_local:
            raise ConnectionError(
                "Cannot call OpenAI API: OPENAI_API_KEY is not set. "
                "The benchmark fails closed when credentials are missing."
            )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key or 'none'}",
        }

        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": formatted_messages,
            "temperature": self.temperature,
        }
        if tools:
            payload["tools"] = tools

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.base_url, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API error HTTP {err.code}: {err_body}") from err
        except Exception as err:
            raise ConnectionError(f"OpenAI network error: {err}") from err

        raw_usage = resp_data.get("usage", {})
        prompt_details = raw_usage.get("prompt_tokens_details", {})
        cached_tok = prompt_details.get("cached_tokens", 0)
        completion_details = raw_usage.get("completion_tokens_details", {})
        reasoning_tok = completion_details.get("reasoning_tokens", 0)

        usage = ProviderTokenUsage(
            input_tokens=raw_usage.get("prompt_tokens", 0),
            output_tokens=raw_usage.get("completion_tokens", 0),
            cached_tokens=cached_tok,
            reasoning_tokens=reasoning_tok,
            total_tokens=raw_usage.get("total_tokens", 0),
            raw_metadata=raw_usage,
        )

        choices = resp_data.get("choices", [])
        choice = choices[0] if choices else {}
        message_obj = choice.get("message", {})
        content = message_obj.get("content")
        finish_reason = choice.get("finish_reason", "stop")

        tool_calls: List[ToolCallRequest] = []
        for tc in message_obj.get("tool_calls", []):
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except Exception:
                args = {"raw_arguments": fn.get("arguments", "")}
            tool_calls.append(ToolCallRequest(
                id=tc.get("id", f"call_{len(tool_calls)+1}"),
                name=fn.get("name", ""),
                arguments=args,
            ))

        actual_model = resp_data.get("model", self.model_name)
        req_id = resp_data.get("id")
        cost = self.calculate_cost_usd(usage)

        return ProviderResponse(
            provider="openai",
            requested_model=self.model_name,
            actual_model=actual_model,
            request_id=req_id,
            finish_reason=finish_reason,
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            cost_usd=cost,
            raw_response=self._sanitize_dict(resp_data),
        )
