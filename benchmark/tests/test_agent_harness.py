"""
test_agent_harness.py — Unit tests for Level 2 Agent Harness data models and costing.
"""
import pytest

from benchmark.agent.agent_interface import (
    AgentResult,
    TokenUsage,
    ToolCallRecord,
    calculate_cost_usd,
)
from benchmark.agent.test_agent import TestAgent


def test_token_usage_aggregation():
    t1 = TokenUsage(input_tokens=1000, output_tokens=200, cached_tokens=500, reasoning_tokens=50, total_tokens=1200)
    t2 = TokenUsage(input_tokens=800, output_tokens=150, cached_tokens=300, reasoning_tokens=30, total_tokens=950)

    t1.add(t2)
    assert t1.input_tokens == 1800
    assert t1.output_tokens == 350
    assert t1.cached_tokens == 800
    assert t1.reasoning_tokens == 80
    assert t1.total_tokens == 2150


def test_calculate_cost_usd():
    # Claude 3.5 Sonnet: $3.00/M in, $15.00/M out, $0.30/M cache
    usage = TokenUsage(
        input_tokens=1_000_000,
        output_tokens=100_000,
        cached_tokens=500_000,
        total_tokens=1_100_000,
    )
    # Regular input: 500k @ $3/M = $1.50
    # Cached input: 500k @ $0.30/M = $0.15
    # Output: 100k @ $15/M = $1.50
    # Total = 1.50 + 0.15 + 1.50 = 3.15
    cost = calculate_cost_usd("claude-3-5-sonnet-20241022", usage)
    assert pytest.approx(cost, 0.001) == 3.15


def test_agent_result_serialization():
    usage = TokenUsage(input_tokens=500, output_tokens=100, total_tokens=600)
    tool = ToolCallRecord(name="view_file", arguments={"path": "main.py"}, output="code", turn=1)
    res = AgentResult(
        task_id="test_task",
        condition="the_judge",
        model="test-model",
        success=True,
        final_verdict="PASS",
        stop_reason="VERIFIED_PASS",
        turns=2,
        tool_calls=[tool],
        token_usage=usage,
        cost_usd=0.005,
    )

    d = res.to_dict()
    assert d["task_id"] == "test_task"
    assert d["success"] is True
    assert len(d["tool_calls"]) == 1
    assert d["tool_calls"][0]["name"] == "view_file"
    assert d["token_usage"]["total_tokens"] == 600
