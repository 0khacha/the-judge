import os
import shutil
from typing import Any, Dict, Optional


class AgentSimulator:
    """Simulates AI Coding Agent behaviors for controlled empirical experiments."""

    def __init__(self, persona: str = "competent"):
        self.persona = persona

    def repair_code(self, task_dir: str, main_module_name: str, feedback: Dict[str, Any], round_num: int) -> bool:
        """Simulates agent repair attempt given structured findings feedback."""
        main_path = os.path.join(task_dir, main_module_name)
        repaired_path = os.path.join(task_dir, "repaired_code.txt")

        if self.persona == "overconfident":
            # Agent claims to fix code but makes no changes
            return True

        if self.persona == "careless":
            # Careless agent only repairs on even rounds or partial edit
            if round_num % 2 == 1 and os.path.exists(repaired_path):
                shutil.copyfile(repaired_path, main_path)
            return True

        if self.persona == "regression_prone":
            # Fixes bug but adds a comment breaking syntax or state in round 2
            if os.path.exists(repaired_path):
                shutil.copyfile(repaired_path, main_path)
            if round_num == 2:
                with open(main_path, "a", encoding="utf-8") as f:
                    f.write("\n# Regression introduced\n")
            return True

        if self.persona == "competent":
            # Competent agent reads structured findings and applies repaired code
            if os.path.exists(repaired_path):
                shutil.copyfile(repaired_path, main_path)
                return True
            return False

        return False
