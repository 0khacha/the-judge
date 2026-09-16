from .agent_adapter import AgentAdapter
from .repair_loop import AgentImprovementLoop, AgentRepairLoop, QualityEvaluator
from .demo import run_demo
from .hooks import install_hook, uninstall_hook
from .ide import generate_vscode_tasks
from .watcher import watch_workspace

__all__ = [
    "AgentAdapter",
    "AgentImprovementLoop",
    "AgentRepairLoop",
    "QualityEvaluator",
    "run_demo",
    "install_hook",
    "uninstall_hook",
    "generate_vscode_tasks",
    "watch_workspace",
]
