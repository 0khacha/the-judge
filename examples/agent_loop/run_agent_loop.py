"""The repair loop with your own repair step, in about 40 lines.

`improve(repair_func=...)` verifies the workspace, hands the verdict to your callback,
verifies again after the callback changed something, and stops at PASS. A real agent
would read feedback["next_actions"] and edit code; this callback applies one fix so the
example runs anywhere, offline, in a few seconds.

    python examples/agent-loop/run_agent_loop.py
"""

import os
import tempfile

from the_judge import improve
from the_judge.api import freeze

STUB = "def add(a, b):\n    raise NotImplementedError\n"
BUGGY = "def add(a, b):\n    return a - b  # bug: subtraction\n"
FIXED = "def add(a, b):\n    return a + b\n"
TESTS = (
    "from calc import add\n\n\n"
    "def test_add():\n    assert add(2, 3) == 5\n\n\n"
    "def test_add_negative():\n    assert add(-2, -7) == -9\n"
)


def repair(workspace: str, feedback: dict) -> bool:
    """Act on the judge's first next action. Return True when a change was made."""
    action = feedback["next_actions"][0]
    print(f"  judge says: {feedback['decision']} -> [{action['action']}] {action['detail'].splitlines()[0][:60]}")
    if action["action"] == "fix_code":
        with open(os.path.join(workspace, "calc.py"), "w", encoding="utf-8") as f:
            f.write(FIXED)
        print("  repair: fixed calc.add")
        return True
    return False


with tempfile.TemporaryDirectory() as ws:
    with open(os.path.join(ws, "calc.py"), "w", encoding="utf-8") as f:
        f.write(STUB)
    with open(os.path.join(ws, "test_calc.py"), "w", encoding="utf-8") as f:
        f.write(TESTS)
    freeze(ws)  # 1. tests are fixed before the implementation
    with open(os.path.join(ws, "calc.py"), "w", encoding="utf-8") as f:
        f.write(BUGGY)  # 2. the implementation arrives, with a bug

    result = improve(ws, repair_func=repair, max_rounds=3)  # 3. verify -> repair -> verify

    print(f"outcome: {result['outcome']}  verdict: {result['final_decision']}  "
          f"rounds: {result['total_rounds']}")
