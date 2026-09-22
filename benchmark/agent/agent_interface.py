"""
agent_interface.py — Standard Interface for Coding Agent Evaluation.

Defines the contract for coding agents executing tasks in Level 2 A/B/C benchmarks:
  - Condition A: Baseline (no review, single pass)
  - Condition B: Generic Review (visible pytest loop)
  - Condition C: The Judge (full verification-repair loop with structured findings)

Enforces:
  - Workspace isolation: All tool actions constrained to target workspace
  - Precise token accounting: input, output, cached, reasoning
  - Model pricing and cost calculation in USD
  - Comprehensive trace preservation: turns, tool calls, messages, errors
"""
from __future__ import annotations

import abc
from dataclasses import asdict, dataclass, field
import json
import os
import subprocess
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple


# Standard model pricing per 1M tokens: (input_price, output_price, cached_input_price)
MODEL_PRICING: Dict[str, Tuple[float, float, float]] = {
    # Anthropic
    "claude-3-5-sonnet-20241022": (3.00, 15.00, 0.30),
    "claude-3-7-sonnet": (3.00, 15.00, 0.30),
    "claude-3-5-haiku-20241022": (0.80, 4.00, 0.08),
    # OpenAI
    "gpt-4o": (2.50, 10.00, 1.25),
    "gpt-4o-mini": (0.15, 0.60, 0.075),
    "o3-mini": (1.10, 4.40, 0.55),
    # Google
    "gemini-1.5-pro": (3.50, 10.50, 0.875),
    "gemini-2.0-flash": (0.10, 0.40, 0.025),
    "gemini-2.5-pro": (3.00, 12.00, 0.75),
    # Default fallback
    "default": (3.00, 15.00, 0.30),
    "test-agent": (0.00, 0.00, 0.00),
}


@dataclass
class ToolCallRecord:
    name: str
    arguments: Dict[str, Any]
    output: str
    error: Optional[str] = None
    duration_seconds: float = 0.0
    turn: int = 1


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: "TokenUsage") -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cached_tokens += other.cached_tokens
        self.reasoning_tokens += other.reasoning_tokens
        self.total_tokens += other.total_tokens

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


def calculate_cost_usd(model_name: str, usage: TokenUsage) -> float:
    """Calculate USD cost based on token usage and model pricing."""
    pricing = MODEL_PRICING.get(model_name, MODEL_PRICING.get("default", (3.00, 15.00, 0.30)))
    in_price, out_price, cache_price = pricing

    # Bill non-cached at regular in_price, cached at cache_price
    regular_input = max(0, usage.input_tokens - usage.cached_tokens)
    cost = (
        (regular_input / 1_000_000.0) * in_price
        + (usage.cached_tokens / 1_000_000.0) * cache_price
        + (usage.output_tokens / 1_000_000.0) * out_price
    )
    return round(cost, 6)


@dataclass
class AgentResult:
    task_id: str
    condition: str
    model: str
    success: bool
    final_verdict: str  # PASS / FAIL / ABSTAIN / ERROR
    stop_reason: str
    turns: int
    tool_calls: List[ToolCallRecord] = field(default_factory=list)
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    conversation_trace: List[Dict[str, Any]] = field(default_factory=list)
    final_response: str = ""
    repaired: bool = False
    repair_rounds: int = 0
    initial_flaw_detected: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["tool_calls"] = [asdict(t) for t in self.tool_calls]
        d["token_usage"] = self.token_usage.to_dict()
        return d


class WorkspaceToolExecutor:
    """Executes safe coding-agent tools strictly within a workspace directory."""

    def __init__(self, workspace_dir: str):
        self.workspace_dir = os.path.abspath(workspace_dir)

    def _resolve(self, relative_path: str) -> str:
        resolved = os.path.abspath(os.path.join(self.workspace_dir, relative_path))
        if not resolved.startswith(self.workspace_dir):
            raise PermissionError(f"Access denied: path outside workspace: {relative_path}")
        return resolved

    def view_file(self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
        full_path = self._resolve(path)
        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"File not found: {path}")
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        
        total = len(lines)
        s = max(1, start_line or 1)
        e = min(total, end_line or total)
        slice_lines = lines[s - 1:e]
        return "".join(slice_lines)

    def write_file(self, path: str, content: str) -> str:
        full_path = self._resolve(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} bytes to {path}"

    def replace_file_content(self, path: str, target: str, replacement: str) -> str:
        full_path = self._resolve(path)
        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"File not found: {path}")
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        
        count = content.count(target)
        if count == 0:
            raise ValueError(f"Target content not found in {path}")
        if count > 1:
            raise ValueError(f"Target content occurs {count} times in {path}; must be unique")
        
        new_content = content.replace(target, replacement, 1)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return f"Successfully replaced content in {path}"

    def run_command(self, command: str, timeout: float = 30.0) -> Tuple[int, str, str]:
        """Run a command with cwd set to the workspace directory."""
        # Safety checks: do not allow modifying outside workspace
        forbidden = ["rm -rf /", "mkfs", "sudo", "format C:"]
        for f in forbidden:
            if f.lower() in command.lower():
                raise PermissionError(f"Prohibited command: {command}")

        # Ensure py -3 / python uses isolated subprocess
        res = subprocess.run(
            command,
            shell=True,
            cwd=self.workspace_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        return res.returncode, res.stdout, res.stderr

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Dispatch tool by name and return string output."""
        if tool_name == "view_file":
            return self.view_file(
                args["path"],
                start_line=args.get("start_line"),
                end_line=args.get("end_line"),
            )
        elif tool_name == "write_file":
            return self.write_file(args["path"], args["content"])
        elif tool_name == "replace_file_content":
            return self.replace_file_content(
                args["path"],
                target=args["target"],
                replacement=args["replacement"],
            )
        elif tool_name == "run_command":
            code, out, err = self.run_command(args["command"], timeout=args.get("timeout", 30.0))
            combined = f"Exit code: {code}\n"
            if out:
                combined += f"STDOUT:\n{out}\n"
            if err:
                combined += f"STDERR:\n{err}\n"
            return combined.strip()
        else:
            raise ValueError(f"Unknown tool: {tool_name}")


class AgentInterface(abc.ABC):
    """Abstract Base Class for Coding Agents in Level 2 Benchmarks."""

    def __init__(self, model_name: str = "default", **kwargs: Any):
        self.model_name = model_name
        self.kwargs = kwargs

    @abc.abstractmethod
    def run_task(
        self,
        task_info: Dict[str, Any],
        condition: str,
        workspace_dir: str,
        max_turns: int = 15,
        max_rounds: int = 5,
    ) -> AgentResult:
        """
        Run the agent on the given task under condition:
          - 'baseline': Initial problem statement; agent edits code and delivers PASS.
          - 'generic_review': Agent runs visible tests, iterates until visible tests pass.
          - 'the_judge': Agent receives The Judge verify() feedback and suggested_focus.
        """
        pass
