"""
base_provider.py — Abstract Base Provider for Real LLM Communication.

Enforces:
  - Exact token extraction from provider responses (no synthetic proxies)
  - Proof of model identity (requested vs actual model identifier, request IDs)
  - Tool call extraction directly from structured model outputs
  - Sanitized logging (no API keys in traces)
  - Strict typing and serializable schemas
"""
from __future__ import annotations

import abc
from dataclasses import asdict, dataclass, field
import json
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ToolCallRequest:
    """A tool call requested directly by the model in its response."""
    id: str
    name: str
    arguments: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderTokenUsage:
    """Exact token counts reported directly by the provider API."""
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderResponse:
    """Standardized response object from any supported LLM provider."""
    provider: str
    requested_model: str
    actual_model: str
    request_id: Optional[str]
    finish_reason: str
    content: Optional[str]
    tool_calls: List[ToolCallRequest] = field(default_factory=list)
    usage: ProviderTokenUsage = field(default_factory=lambda: ProviderTokenUsage(0, 0))
    cost_usd: float = 0.0
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["tool_calls"] = [t.to_dict() for t in self.tool_calls]
        d["usage"] = self.usage.to_dict()
        return d


class AgentProvider(abc.ABC):
    """Abstract Base Class for LLM Provider Integrations."""

    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        temperature: float = 0.0,
        **kwargs: Any,
    ):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.temperature = temperature
        self.kwargs = kwargs

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g., 'anthropic', 'openai', 'gemini')."""
        pass

    @abc.abstractmethod
    def send_turn(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> ProviderResponse:
        """
        Execute a real API call to the model provider.
        Must raise an exception or fail-closed if the network request fails.
        """
        pass

    @abc.abstractmethod
    def calculate_cost_usd(self, usage: ProviderTokenUsage) -> float:
        """Calculate USD expenditure based on verified official pricing."""
        pass

    @abc.abstractmethod
    def health_check(self) -> Tuple[bool, str]:
        """Verify API connectivity and authentication with a minimal probe."""
        pass

    def _sanitize_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Strip API keys, authorization tokens, and credentials from logs."""
        clean = {}
        for k, v in d.items():
            if any(secret_term in k.lower() for secret_term in ("key", "auth", "token", "secret", "bearer")):
                clean[k] = "[REDACTED]"
            elif isinstance(v, dict):
                clean[k] = self._sanitize_dict(v)
            else:
                clean[k] = v
        return clean
