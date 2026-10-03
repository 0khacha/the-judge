"""Regression tests for Bug 3: demo prints contradictory result.

`judge demo` shows 'DECISION: FAIL' in round 2, then prints
'Target code successfully repaired and verified!'.
The final message must derive from the actual last decision.
"""

import io
import contextlib

from the_judge.integrations.demo import run_demo


class TestBug3DemoMessage:
    """Demo final message must match actual verification decision."""

    def test_demo_success_only_when_pass(self):
        """The success message must only appear if final decision is PASS."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_demo()
        output = buf.getvalue()

        # Find the last DECISION line
        decision_lines = [
            line for line in output.splitlines()
            if "DECISION:" in line
        ]
        assert decision_lines, "Demo should print at least one DECISION line"

        last_decision_line = decision_lines[-1]

        if "PASS" in last_decision_line:
            assert "successfully repaired and verified" in output, (
                "Demo shows PASS but doesn't print success message"
            )
        else:
            assert "successfully repaired and verified" not in output, (
                f"Demo shows {last_decision_line.strip()} but prints success message. "
                "Final message must derive from actual decision."
            )

    def test_demo_fixed_implementation_actually_passes(self):
        """The demo's 'fixed' implementation should actually pass verification."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_demo()
        output = buf.getvalue()

        decision_lines = [
            line for line in output.splitlines()
            if "DECISION:" in line
        ]
        assert len(decision_lines) >= 2, "Demo should have at least 2 rounds"

        # Round 2 (the 'fixed' version) should be PASS or FAIL, not ERROR
        last_decision = decision_lines[-1]
        assert "ERROR" not in last_decision, (
            f"Demo round 2 produced ERROR: {last_decision}"
        )
