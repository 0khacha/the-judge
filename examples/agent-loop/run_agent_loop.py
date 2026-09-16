import os
import tempfile
from the_judge.integrations.agent_adapter import AgentAdapter
from the_judge.integrations.repair_loop import AgentRepairLoop

# Initial buggy code written by an agent
initial_code = """class Calculator:
    def add(self, a, b):
        return a - b  # Bug: subtraction instead of addition
"""

repaired_code = """class Calculator:
    def add(self, a, b):
        return a + b  # Fixed: addition
"""

def agent_callback(workspace_dir: str, feedback: dict) -> bool:
    print(f"[Agent Callback] Received feedback with {len(feedback.get('findings', []))} findings.")
    print("[Agent Callback] Applying code fix...")
    target_path = os.path.join(workspace_dir, "calc.py")
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(repaired_code)
    return True

with tempfile.TemporaryDirectory() as tmp_dir:
    target_path = os.path.join(tmp_dir, "calc.py")
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(initial_code)

    adapter = AgentAdapter()
    repair_loop = AgentRepairLoop(adapter=adapter, max_rounds=3)

    print("Starting multi-round agent repair loop...")
    result = repair_loop.run_repair_loop(tmp_dir, agent_callback)

    print(f"Final Outcome: {result['outcome']}")
    print(f"Total Rounds:  {result['total_rounds']}")
