"""
gemini_provider.py — Google Gemini API Provider Adapter.
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

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

GEMINI_PRICING: Dict[str, Tuple[float, float, float]] = {
    "gemini-1.5-pro": (3.50, 10.50, 0.875),
    "gemini-2.0-flash": (0.10, 0.40, 0.025),
    "gemini-2.5-pro": (3.00, 12.00, 0.75),
    "default": (0.10, 0.40, 0.025),
}


class GeminiProvider(AgentProvider):
    """Direct HTTP client for Google Gemini REST API."""

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        temperature: float = 0.0,
        **kwargs: Any,
    ):
        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        super().__init__(
            model_name=model_name,
            api_key=key,
            base_url=base_url or GEMINI_BASE_URL,
            timeout=timeout,
            temperature=temperature,
            **kwargs,
        )

    @property
    def provider_name(self) -> str:
        return "gemini"

    def calculate_cost_usd(self, usage: ProviderTokenUsage) -> float:
        pricing = GEMINI_PRICING.get(self.model_name, GEMINI_PRICING["default"])
        in_price, out_price, cache_price = pricing
        reg_in = max(0, usage.input_tokens - usage.cached_tokens)
        cost = (
            (reg_in / 1_000_000.0) * in_price
            + (usage.cached_tokens / 1_000_000.0) * cache_price
            + (usage.output_tokens / 1_000_000.0) * out_price
        )
        return round(cost, 6)

    def health_check(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "GEMINI_API_KEY or GOOGLE_API_KEY is not set"
        try:
            resp = self.send_turn(messages=[{"role": "user", "content": "ping"}])
            return True, f"Connected to {resp.actual_model}"
        except Exception as e:
            return False, f"Gemini connection failed: {e}"

    def send_turn(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> ProviderResponse:
        if not self.api_key:
            raise ConnectionError(
                "Cannot call Gemini API: GEMINI_API_KEY is not set. "
                "The benchmark fails closed when credentials are missing."
            )

        url = f"{self.base_url}/{self.model_name}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        # Format Gemini contents
        contents = []
        for m in messages:
            role = "user" if m.get("role") in ("user", "system") else "model"
            contents.append({
                "role": role,
                "parts": [{"text": m.get("content", "")}],
            })

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": self.temperature},
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        # Convert tools to functionDeclarations
        if tools:
            func_decls = []
            for t in tools:
                fn = t.get("function", t)
                func_decls.append({
                    "name": fn.get("name"),
                    "description": fn.get("description", ""),
                    "parameters": fn.get("parameters", {}),
                })
            payload["tools"] = [{"functionDeclarations": func_decls}]

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini API error HTTP {err.code}: {err_body}") from err
        except Exception as err:
            raise ConnectionError(f"Gemini network error: {err}") from err

        usage_meta = resp_data.get("usageMetadata", {})
        usage = ProviderTokenUsage(
            input_tokens=usage_meta.get("promptTokenCount", 0),
            output_tokens=usage_meta.get("candidatesTokenCount", 0),
            cached_tokens=usage_meta.get("cachedContentTokenCount", 0),
            total_tokens=usage_meta.get("totalTokenCount", 0),
            raw_metadata=usage_meta,
        )

        candidates = resp_data.get("candidates", [])
        cand = candidates[0] if candidates else {}
        content_obj = cand.get("content", {})
        finish_reason = cand.get("finishReason", "STOP")

        text_parts: List[str] = []
        tool_calls: List[ToolCallRequest] = []
        for part in content_obj.get("parts", []):
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append(ToolCallRequest(
                    id=f"call_{len(tool_calls)+1}",
                    name=fc.get("name", ""),
                    arguments=fc.get("args", {}),
                ))

        actual_model = resp_data.get("modelVersion", self.model_name)
        cost = self.calculate_cost_usd(usage)

        return ProviderResponse(
            provider="gemini",
            requested_model=self.model_name,
            actual_model=actual_model,
            request_id=None,
            finish_reason=finish_reason,
            content="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            usage=usage,
            cost_usd=cost,
            raw_response=self._sanitize_dict(resp_data),
        )
