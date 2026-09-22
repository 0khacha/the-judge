"""
test_agent.py — Deterministic & Reproducible Coding Agent for Level 2 Evaluation.

Allows full Level 2 benchmark execution without live API keys:
  - Executes real workspace file tools (view_file, write_file, replace_file_content, run_command)
  - Follows Condition A, B, and C protocols faithfully
  - Produces complete, realistic conversation traces and tool records
  - Simulates token usage and costs matching standard frontier models
  - Demonstrates how real agents react to Judge structured findings and suggested_focus
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from benchmark.agent.agent_interface import (
    AgentInterface,
    AgentResult,
    TokenUsage,
    ToolCallRecord,
    WorkspaceToolExecutor,
    calculate_cost_usd,
)
from benchmark.benchmark_abc.conditions import (
    compute_workspace_hash,
    normalize_blocking_issues,
)
from the_judge.integrations.agent_adapter import AgentAdapter


class TestAgent(AgentInterface):
    """Deterministic agent implementing realistic coding agent behavior."""

    __test__ = False

    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022", **kwargs: Any):
        super().__init__(model_name=model_name, **kwargs)

    def _find_target_py_file(self, workspace_dir: str) -> Optional[str]:
        """Find the primary source file under test in workspace."""
        for f in os.listdir(workspace_dir):
            if f.endswith(".py") and f not in ("apply_fix.py", "conftest.py") and not f.startswith("test_"):
                return f
        return None

    def _simulate_turn_tokens(
        self,
        prompt_len_chars: int,
        response_len_chars: int,
        prior_tokens: int,
    ) -> TokenUsage:
        """Simulate realistic token usage for a turn based on character counts."""
        # Standard rough heuristic: ~4 chars per token
        prompt_tokens = max(500, prompt_len_chars // 4) + prior_tokens
        output_tokens = max(150, response_len_chars // 4)
        cached_tokens = max(0, prior_tokens)  # Prior turns are cached
        reasoning_tokens = max(50, output_tokens // 3)
        total_tokens = prompt_tokens + output_tokens
        return TokenUsage(
            input_tokens=prompt_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            reasoning_tokens=reasoning_tokens,
            total_tokens=total_tokens,
        )

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
        adapter = AgentAdapter(name="DeterministicTestAgent")
        task_id = task_info.get("task_id", os.path.basename(workspace_dir))
        target_file = self._find_target_py_file(workspace_dir)

        total_usage = TokenUsage()
        tool_calls: List[ToolCallRecord] = []
        conversation_trace: List[Dict[str, Any]] = []
        turns = 0
        repair_rounds = 0
        initial_flaw_detected = False
        final_verdict = "PASS"
        stop_reason = "COMPLETED"
        final_response = ""

        # Initial prompt
        user_msg = f"Implement or review the code for {task_id} in workspace {workspace_dir}."
        conversation_trace.append({"role": "user", "content": user_msg})

        # Turn 1: Inspect code
        turns += 1
        t_call_start = time.time()
        if target_file and os.path.isfile(os.path.join(workspace_dir, target_file)):
            file_content = tool_executor.view_file(target_file)
            call_dur = time.time() - t_call_start
            rec = ToolCallRecord(
                name="view_file",
                arguments={"path": target_file},
                output=file_content[:500] + ("..." if len(file_content) > 500 else ""),
                duration_seconds=round(call_dur, 3),
                turn=turns,
            )
            tool_calls.append(rec)
            agent_thought = f"I have inspected {target_file}. The starting implementation is present."
        else:
            agent_thought = "No primary source file found to inspect."

        turn1_usage = self._simulate_turn_tokens(len(user_msg), len(agent_thought), 0)
        total_usage.add(turn1_usage)
        conversation_trace.append({"role": "assistant", "thought": agent_thought})

        # ------------------------------------------------------------------ #
        # Condition A: Baseline
        # ------------------------------------------------------------------ #
        if condition == "baseline":
            # Baseline agent does no active testing or verification; claims PASS
            final_response = "Baseline review complete: source file inspected and confirmed as satisfactory."
            final_verdict = "PASS"
            stop_reason = "NO_REVIEW_BASELINE_PASS"
            conversation_trace.append({"role": "assistant", "content": final_response})

        # ------------------------------------------------------------------ #
        # Condition B: Generic Review
        # ------------------------------------------------------------------ #
        elif condition == "generic_review":
            # Agent runs visible tests via run_command
            turns += 1
            t_call_start = time.time()
            ret_code, stdout, stderr = tool_executor.run_command("py -3 -m pytest visible_tests/")
            call_dur = time.time() - t_call_start

            rec = ToolCallRecord(
                name="run_command",
                arguments={"command": "py -3 -m pytest visible_tests/"},
                output=stdout[:500] if stdout else stderr[:500],
                duration_seconds=round(call_dur, 3),
                turn=turns,
            )
            tool_calls.append(rec)

            turn2_usage = self._simulate_turn_tokens(len(stdout) + 200, 300, total_usage.input_tokens)
            total_usage.add(turn2_usage)

            if ret_code == 0:
                final_response = "All visible unit tests passed. Solution verified and approved."
                final_verdict = "PASS"
                stop_reason = "VISIBLE_TESTS_PASSED"
            else:
                final_response = "Visible unit tests failed."
                final_verdict = "FAIL"
                stop_reason = "VISIBLE_TESTS_FAILED"
            conversation_trace.append({"role": "assistant", "content": final_response})

        # ------------------------------------------------------------------ #
        # Condition C: The Judge
        # ------------------------------------------------------------------ #
        elif condition == "the_judge":
            previous_evidence = None
            last_norm_blocking = None
            last_ws_hash = None
            last_score = None

            for round_num in range(1, max_rounds + 1):
                turns += 1
                judge_res = adapter.verify_workspace(
                    workspace_dir,
                    task_spec=task_info,
                    previous_evidence=previous_evidence,
                )
                verdict = judge_res.get("decision", "ERROR")
                score = judge_res.get("numeric_score", 0.0)
                findings = judge_res.get("findings", [])
                blocking = judge_res.get("blocking_issues", [])
                norm_blocking = normalize_blocking_issues(blocking)
                ws_hash = compute_workspace_hash(workspace_dir)

                feedback_prompt = adapter.format_agent_prompt_feedback(judge_res)
                conversation_trace.append({
                    "role": "environment",
                    "content": feedback_prompt,
                    "round": round_num,
                })

                round_usage = self._simulate_turn_tokens(len(feedback_prompt), 400, total_usage.input_tokens)
                total_usage.add(round_usage)

                if round_num == 1 and verdict != "PASS":
                    initial_flaw_detected = True

                if verdict == "PASS":
                    final_verdict = "PASS"
                    stop_reason = "VERIFIED_PASS"
                    final_response = f"The Judge verified all contracts in round {round_num}. Score: {score:.1f}."
                    conversation_trace.append({"role": "assistant", "content": final_response})
                    break

                # Check for stagnation: if score, normalized blocking issues, and workspace hash are unchanged
                if round_num > 1:
                    score_same = (score == last_score)
                    blocking_same = (norm_blocking == last_norm_blocking)
                    hash_same = (ws_hash == last_ws_hash)
                    if score_same and blocking_same and hash_same:
                        stop_reason = "STAGNATION"
                        final_verdict = verdict
                        final_response = f"Stagnation detected in round {round_num}: verifier feedback is identical."
                        conversation_trace.append({"role": "assistant", "content": final_response})
                        break

                last_score = score
                last_norm_blocking = norm_blocking
                last_ws_hash = ws_hash

                # Attempt repair using findings guidance
                repair_rounds += 1
                turns += 1
                repair_script = os.path.join(workspace_dir, "apply_fix.py")
                t_repair_start = time.time()

                if os.path.isfile(repair_script):
                    # Agent uses suggested_focus and applies the required code modifications
                    code, out, err = tool_executor.run_command("py -3 apply_fix.py")
                    r_dur = time.time() - t_repair_start
                    rec = ToolCallRecord(
                        name="replace_file_content",
                        arguments={"script": "apply_fix.py", "reason": "Repair per Judge suggested_focus"},
                        output=out or "Code repair applied",
                        duration_seconds=round(r_dur, 3),
                        turn=turns,
                    )
                    tool_calls.append(rec)
                    agent_thought = (
                        f"Round {round_num} repair: Addressed Judge findings "
                        f"({len(findings)} issues). Replaced defective implementation."
                    )
                else:
                    agent_thought = "No repair strategy found for identified defects."
                    stop_reason = "NO_REPAIR_AVAILABLE"
                    final_verdict = verdict
                    break

                conversation_trace.append({"role": "assistant", "thought": agent_thought})
                repair_usage = self._simulate_turn_tokens(300, 300, total_usage.input_tokens)
                total_usage.add(repair_usage)

                new_ws_hash = compute_workspace_hash(workspace_dir)
                if new_ws_hash == ws_hash:
                    # Idempotent edit made 0 file changes
                    stop_reason = "STAGNATION"
                    final_verdict = verdict
                    final_response = "Repair action made no further file modifications. Terminating loop."
                    conversation_trace.append({"role": "assistant", "content": final_response})
                    break

                last_ws_hash = new_ws_hash
                previous_evidence = {"round": round_num, "verdict": verdict}
            else:
                final_verdict = verdict
                stop_reason = "MAX_ROUNDS_REACHED"
                final_response = f"Max verification rounds ({max_rounds}) reached."
                conversation_trace.append({"role": "assistant", "content": final_response})

        duration = time.time() - t0
        cost = calculate_cost_usd(self.model_name, total_usage)

        return AgentResult(
            task_id=task_id,
            condition=condition,
            model=self.model_name,
            success=(final_verdict == "PASS"),
            final_verdict=final_verdict,
            stop_reason=stop_reason,
            turns=turns,
            tool_calls=tool_calls,
            token_usage=total_usage,
            cost_usd=cost,
            duration_seconds=duration,
            conversation_trace=conversation_trace,
            final_response=final_response,
            repaired=(repair_rounds > 0),
            repair_rounds=repair_rounds,
            initial_flaw_detected=initial_flaw_detected,
            metadata={"agent_type": "test", "simulation": True},
        )
