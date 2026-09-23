"""IDE integration generators for The Judge.

Generates configuration files for VS Code (tasks.json) to run
verification directly from the command palette.
"""

import json
import os

VSCODE_TASKS = {
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Judge: Verify Workspace",
            "type": "shell",
            "command": "judge verify . --json",
            "group": {
                "kind": "test",
                "isDefault": True,
            },
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
                "clear": True,
            },
            "problemMatcher": {
                "owner": "the-judge",
                "fileLocation": ["relative", "${workspaceFolder}"],
                "pattern": {
                    "regexp": "^\\s*Suggested Focus:\\s*(.+)$",
                    "message": 1,
                },
            },
        },
        {
            "label": "Judge: Verify (Human-Readable)",
            "type": "shell",
            "command": "judge verify .",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
                "clear": True,
            },
            "problemMatcher": [],
        },
        {
            "label": "Judge: Contract Coverage",
            "type": "shell",
            "command": "judge contract .",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "problemMatcher": [],
        },
        {
            "label": "Judge: Watch Mode",
            "type": "shell",
            "command": "judge watch .",
            "isBackground": True,
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "dedicated",
            },
            "problemMatcher": [],
        },
    ],
}


def generate_vscode_tasks(workspace_path: str) -> str:
    """Generate .vscode/tasks.json with Judge verification tasks.

    Args:
        workspace_path: Root workspace directory.

    Returns:
        Path to the generated tasks.json file.

    Raises:
        FileExistsError: If tasks.json already exists with non-Judge content.
    """
    vscode_dir = os.path.join(os.path.abspath(workspace_path), ".vscode")
    os.makedirs(vscode_dir, exist_ok=True)

    tasks_path = os.path.join(vscode_dir, "tasks.json")

    if os.path.exists(tasks_path):
        with open(tasks_path, encoding="utf-8") as f:
            try:
                existing = json.load(f)
                existing_labels = {t.get("label", "") for t in existing.get("tasks", [])}
                if any("Judge:" in label for label in existing_labels):
                    pass  # Overwrite existing Judge tasks
                elif existing.get("tasks"):
                    raise FileExistsError(
                        f"tasks.json already exists at {tasks_path} with non-Judge tasks. "
                        "Merge manually or remove the file first."
                    )
            except json.JSONDecodeError:
                pass  # Overwrite malformed file

    with open(tasks_path, "w", encoding="utf-8") as f:
        json.dump(VSCODE_TASKS, f, indent=2)
        f.write("\n")

    return tasks_path
