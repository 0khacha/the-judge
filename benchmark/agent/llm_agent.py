"""
llm_agent.py — Real Autonomous LLM Coding Agent for Level 2 Evaluation.

Enforces:
  - Genuine provider API communication (Anthropic, OpenAI, Gemini)
  - Tool calling originating strictly from model responses
  - Exact token usage extraction from provider response objects
  - Strict workspace confinement (no access outside workspace_dir)
  - Complete elimination of oracle scripts (no apply_fix.py execution)
  - Equalized interaction budgets across Conditions A, B, and C
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from benchmark.agent.agent_interface import (
    AgentInterface,
    AgentResult,
    TokenUsage,
    ToolCallRecord,
    WorkspaceToolExecutor,
)
from benchmark.agent.providers.base_provider import (
    AgentProvider,
    ProviderResponse,
    ProviderTokenUsage,
    ToolCallRequest,
)
from benchmark.agent.providers.factory import get_provider
from the_judge.integrations.agent_adapter import AgentAdapter

BASE_ENGINEERING_SYSTEM_PROMPT = """You are an expert software engineer tasked with solving a software problem in a repository.
You have access to tools to view, edit, and run tests in your workspace.

Workflow guidelines:
1. Inspect the requirements and relevant code files thoroughly before editing.
2. Implement robust, clean, and bug-free code meeting all requirements.
3. You can execute visible unit tests using `run_command` (e.g. `py -3 -m pytest visible_tests/`).
4. Once you are confident that your changes are complete and correct, provide a final concise explanation of your changes.
"""

GENERIC_REVIEW_ADDITION = """
CRITICAL REVIEW REQUIREMENT:
Before concluding, you must critically review your implementation. Run visible tests, check edge cases,
and verify that no subtle logic errors, state corruption, or regressions exist.
"""

JUDGE_VERIFY_ADDITION = """
QUALITY CONTROL VERIFICATION:
You have access to the `judge_verify` tool. This tool invokes The Judge contract verification engine on your workspace.
After implementing your changes, you should call `judge_verify` to receive structured quality feedback,
failing property checks, and suggested focus areas. Iterate on your implementation if issues are reported.
"""

BASE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "view_file",
            "description": "View file content in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to file"},
                    "start_line": {"type": "integer", "description": "Optional start line (1-based)"},
                    "end_line": {"type": "integer", "description": "Optional end line (1-based)"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite a file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to file"},
                    "content": {"type": "string", "description": "Full file content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_file_content",
            "description": "Replace a unique string chunk in a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to file"},
                    "target": {"type": "string", "description": "Exact text to find and replace"},
                    "replacement": {"type": "string", "description": "Replacement text"},
                },
                "required": ["path", "target", "replacement"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command within the workspace directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                },
                "required": ["command"],
            },
        },
    },
]

JUDGE_TOOL = {
    "type": "function",
    "function": {
        "name": "judge_verify",
        "description": "Run The Judge verification engine on the current workspace to evaluate contract adherence and behavioral properties.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}


class LLMAgent(AgentInterface):
    """Real LLM Coding Agent communicating via concrete AgentProvider."""

    def __init__(
        self,
        provider: Optional[AgentProvider] = None,
        model_name: str = "claude-3-5-sonnet-20241022",
        provider_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ):
        super().__init__(model_name=model_name, **kwargs)
        self.provider = provider or get_provider(
            provider_name=provider_name,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            **kwargs,
        )

    def preflight_check(self) -> Tuple[bool, str]:
        """Verify provider authentication and connectivity fail-closed."""
        return self.provider.health_check()

    def run_task(
        self,
        task_info: Dict[str, Any],
        condition: str,
        workspace_dir: str,
        max_turns: int = 15,
        max_rounds: int = 5,
    ) -> AgentResult:
        t0 = time.time()
        tool_executor = WorkspaceToolExecutor(workspace_dir)
        adapter = AgentAdapter(name="RealLLMAgent")
        task_id = task_info.get("task_id", os.path.basename(workspace_dir))

        # Enforce that apply_fix.py is physically absent
        forbidden_oracle = os.path.join(workspace_dir, "apply_fix.py")
        if os.path.exists(forbidden_oracle):
            raise PermissionError(
                f"Benchmark integrity violation: {forbidden_oracle} is present in agent workspace. "
                "Level 2 agents must never have access to oracle patches."
            )

        # Build tools and system prompt based on condition
        tools = list(BASE_TOOLS)
        system_prompt = BASE_ENGINEERING_SYSTEM_PROMPT

        if condition == "generic_review":
            system_prompt += GENERIC_REVIEW_ADDITION
        elif condition == "the_judge":
            system_prompt += JUDGE_VERIFY_ADDITION
            tools.append(JUDGE_TOOL)

        req_file = os.path.join(workspace_dir, "requirements.md")
        requirements_text = ""
        if os.path.isfile(req_file):
            with open(req_file, "r", encoding="utf-8") as f:
                requirements_text = f.read()

        initial_user_msg = f"Task: {task_id}\n\nRequirements:\n{requirements_text}\n"
        initial_user_msg += "\nPlease solve the task by inspecting the code, making necessary modifications, and verifying your work."

        messages: List[Dict[str, Any]] = [
            {"role": "user", "content": initial_user_msg},
        ]

        total_usage = TokenUsage()
        tool_calls: List[ToolCallRecord] = []
        conversation_trace: List[Dict[str, Any]] = []
        conversation_trace.append({"role": "user", "content": initial_user_msg})

        turns = 0
        repair_rounds = 0
        initial_flaw_detected = False
        final_verdict = "PASS"
        stop_reason = "COMPLETED"
        final_response_text = ""
        actual_model_proven = self.model_name
        request_ids = []

        while turns < max_turns:
            turns += 1

            # Real API call to provider
            try:
                resp: ProviderResponse = self.provider.send_turn(
                    messages=messages,
                    tools=tools,
                    system_prompt=system_prompt,
                )
            except Exception as err:
                # Fail closed: network or API failure
                return AgentResult(
                    task_id=task_id,
                    condition=condition,
                    model=self.model_name,
                    success=False,
                    final_verdict="ERROR",
                    stop_reason=f"PROVIDER_ERROR: {err}",
                    turns=turns,
                    tool_calls=tool_calls,
                    token_usage=total_usage,
                    cost_usd=self.provider.calculate_cost_usd(
                        ProviderTokenUsage(total_usage.input_tokens, total_usage.output_tokens, total_usage.cached_tokens)
                    ),
                    duration_seconds=time.time() - t0,
                    metadata={"error": str(err)},
                )

            actual_model_proven = resp.actual_model
            if resp.request_id:
                request_ids.append(resp.request_id)

            # Record exact provider token usage
            total_usage.input_tokens += resp.usage.input_tokens
            total_usage.output_tokens += resp.usage.output_tokens
            total_usage.cached_tokens += resp.usage.cached_tokens
            total_usage.reasoning_tokens += resp.usage.reasoning_tokens
            total_usage.total_tokens += resp.usage.total_tokens

            # Process response content
            if resp.content:
                final_response_text = resp.content
                conversation_trace.append({"role": "assistant", "content": resp.content})

            # If model made no tool calls, it has finished its work
            if not resp.tool_calls:
                stop_reason = "AGENT_CONCLUDED"
                break

            # Execute model-requested tools
            # Add assistant message with tool_calls for OpenAI / Anthropic format
            tool_call_dicts = []
            for tc in resp.tool_calls:
                tool_call_dicts.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                })
            messages.append({"role": "assistant", "content": resp.content or "", "tool_calls": tool_call_dicts})

            for tc in resp.tool_calls:
                t_tool_start = time.time()
                tool_err = None
                tool_out = ""

                # Handle Judge Verify tool
                if tc.name == "judge_verify":
                    repair_rounds += 1
                    try:
                        j_res = adapter.verify_workspace(workspace_dir, task_spec=task_info)
                        tool_out = adapter.format_agent_prompt_feedback(j_res)
                        if j_res.get("decision") != "PASS":
                            initial_flaw_detected = True
                    except Exception as j_err:
                        tool_err = str(j_err)
                        tool_out = f"The Judge error: {j_err}"
                else:
                    # Execute standard workspace tool
                    try:
                        tool_out = tool_executor.execute_tool(tc.name, tc.arguments)
                    except Exception as exec_err:
                        tool_err = str(exec_err)
                        tool_out = f"Tool execution error: {exec_err}"

                tool_dur = time.time() - t_tool_start

                # Record tool call strictly originating from model request
                rec = ToolCallRecord(
                    name=tc.name,
                    arguments=tc.arguments,
                    output=tool_out[:1000] + ("..." if len(tool_out) > 1000 else ""),
                    error=tool_err,
                    duration_seconds=round(tool_dur, 3),
                    turn=turns,
                )
                tool_calls.append(rec)

                # Append tool result to conversation history
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.name,
                    "content": tool_out,
                })
                conversation_trace.append({
                    "role": "tool",
                    "name": tc.name,
                    "content": tool_out,
                    "error": tool_err,
                })

        else:
            stop_reason = "MAX_TURNS_REACHED"

        cost_usd = self.provider.calculate_cost_usd(
            ProviderTokenUsage(total_usage.input_tokens, total_usage.output_tokens, total_usage.cached_tokens)
        )
        duration = time.time() - t0

        return AgentResult(
            task_id=task_id,
            condition=condition,
            model=self.model_name,
            success=True,
            final_verdict=final_verdict,
            stop_reason=stop_reason,
            turns=turns,
            tool_calls=tool_calls,
            token_usage=total_usage,
            cost_usd=cost_usd,
            duration_seconds=duration,
            conversation_trace=conversation_trace,
            final_response=final_response_text,
            repaired=(repair_rounds > 0),
            repair_rounds=repair_rounds,
            initial_flaw_detected=initial_flaw_detected,
            metadata={
                "provider": self.provider.provider_name,
                "requested_model": self.model_name,
                "actual_model": actual_model_proven,
                "request_ids": request_ids,
            },
        )
