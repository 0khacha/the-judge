"""Drive an external coding agent from ``judge improve --agent``.

The Judge cannot fix code by itself: deciding what correct behaviour is needs the
specification and judgement. What it can do is tell an agent exactly what is missing
(``next_actions``) and check the result independently. This module turns one round of
verification into a prompt, runs the agent command in the workspace, and reports whether
the agent finished; the repair loop then re-verifies.

The command is run through the shell in the workspace directory. The prompt is passed on
stdin, or, when the command contains ``{prompt_file}``, written to a temporary file whose
path replaces that placeholder (for agents that read a message file).
"""

import contextlib
import os
import shutil
import subprocess
import tempfile
from typing import Any, Callable, Optional

AUTO = "auto"
DEFAULT_AGENT_TIMEOUT = 1800  # seconds per agent round

# Agents detected for ``--agent`` without a command, in order of preference.
KNOWN_AGENTS: tuple[tuple[str, str], ...] = (
    # acceptEdits alone lets the agent edit but not run anything; allow it to run the
    # tests and the judge so it can check its own work before the judge re-verifies.
    ("claude", 'claude -p --permission-mode acceptEdits --allowedTools '
               '"Bash(judge verify:*)" "Bash(python -m pytest:*)" "Bash(pytest:*)"'),
)

RULES = """Rules (from the verification-repair protocol in AGENTS.md):
- Tests listed in .judge/frozen.json are frozen. Never edit, skip, delete, parametrize away
  or weaken them. If a frozen test fails, change the implementation.
- New tests are welcome. Take expected results from the specification (TASK.md, SPEC.md,
  REQUIREMENTS.md, judge.json, README), never from what the code returns now.
- When a new test you wrote from the specification fails, the code is wrong: fix the code.
- Do not modify anything inside a `the_judge/` directory or `.judge/`.
- You may run `judge verify . --json` to check your work. Do not run `judge improve`.
- Make the changes, then stop. The Judge re-verifies after you finish."""


def resolve_agent_command(command: Optional[str]) -> str:
    """Return the shell command to run, detecting a known agent for ``auto``.

    Raises ValueError when ``auto`` is requested and no known agent is on PATH.
    """
    if command and command != AUTO:
        return command
    for executable, cmd in KNOWN_AGENTS:
        if shutil.which(executable):
            return cmd
    names = ", ".join(name for name, _ in KNOWN_AGENTS)
    raise ValueError(
        f"No coding agent found on PATH (looked for: {names}). Pass the command explicitly, "
        'for example --agent "claude -p --permission-mode acceptEdits" or '
        '--agent "aider --yes-always --message-file {prompt_file}".'
    )


def build_prompt(feedback: dict[str, Any]) -> str:
    """Build the agent prompt from one round of repair-loop feedback."""
    decision = feedback.get("verification_decision") or feedback.get("decision", "UNKNOWN")
    score = feedback.get("numeric_score")
    lines = [
        "The Judge, an independent verifier, checked the project in the current directory.",
        f"Verdict: {decision}" + (f" (score {score:.1f}/100)" if isinstance(score, (int, float)) else ""),
        "",
    ]

    actions = [a for a in feedback.get("next_actions", [])
               if a.get("action") not in ("re_verify", "done", "stop")]
    if actions:
        lines.append("Do these steps, in order:")
        for idx, action in enumerate(actions, 1):
            head = f"{idx}. [{action.get('action')}] {action.get('detail', '')}"
            if action.get("test"):
                head += f" (test: {action['test']})"
            lines.append(head)
            if action.get("guidance"):
                lines.append(f"   How: {action['guidance']}")
            if action.get("command"):
                lines.append(f"   Command: {action['command']}")
        lines.append("")

    findings = [f for f in feedback.get("findings", [])
                if f.get("severity") in ("blocking", "critical", "high")]
    if findings:
        lines.append("Blocking findings:")
        for f in findings[:10]:
            lines.append(f"- {f.get('description', '')}")
            if f.get("observed"):
                lines.append(f"  Observed: {str(f['observed'])[:400]}")
        lines.append("")

    critique = feedback.get("critique") or {}
    priorities = critique.get("improvement_priority", []) if isinstance(critique, dict) else []
    if priorities:
        lines.append("Further weaknesses an independent critique found (lower priority):")
        for f in priorities[:5]:
            action = f.get("suggested_action")
            lines.append(f"- {f.get('description', '')}" + (f" -> {action}" if action else ""))
        lines.append("")

    quality = feedback.get("quality_evaluation") or {}
    if decision == "PASS" and quality:
        lines.append(f"The verdict is PASS but the quality bar is not met yet "
                     f"({quality.get('score')} < {quality.get('threshold')}).")
        lines.append("")

    if not actions and not findings and not priorities:
        lines.append("No specific action was reported. Review the tests against the "
                     "specification and add the missing checks.")
        lines.append("")

    lines.append(RULES)
    return "\n".join(lines)


def run_agent(command: str, prompt: str, workspace: str,
              timeout: int = DEFAULT_AGENT_TIMEOUT) -> dict[str, Any]:
    """Run the agent command once in ``workspace`` and return its outcome."""
    cwd = workspace if os.path.isdir(workspace) else os.path.dirname(os.path.abspath(workspace))
    prompt_path = None
    stdin_text: Optional[str] = prompt
    if "{prompt_file}" in command:
        fd, prompt_path = tempfile.mkstemp(prefix="judge_prompt_", suffix=".md")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(prompt)
        command = command.replace("{prompt_file}", prompt_path)
        stdin_text = None
    try:
        # Without a prompt on stdin, give the agent an empty stdin rather than ours
        # (which may be closed or invalid when the judge itself runs non-interactively).
        stdin_kw: dict[str, Any] = (
            {"input": stdin_text} if stdin_text is not None else {"stdin": subprocess.DEVNULL}
        )
        proc = subprocess.run(
            command, shell=True, cwd=cwd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, **stdin_kw,
        )
        return {"exit_code": proc.returncode, "timed_out": False,
                "stdout": proc.stdout or "", "stderr": proc.stderr or ""}
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if isinstance(exc.stdout, str) else ""
        return {"exit_code": None, "timed_out": True, "stdout": out, "stderr": ""}
    finally:
        if prompt_path:
            with contextlib.suppress(OSError):
                os.remove(prompt_path)


def make_agent_repair(
    command: str,
    timeout: int = DEFAULT_AGENT_TIMEOUT,
    on_round: Optional[Callable[[dict[str, Any]], None]] = None,
) -> Callable[[str, dict[str, Any]], dict[str, Any]]:
    """Return a repair callback for AgentRepairLoop that delegates to ``command``."""

    def repair(workspace: str, feedback: dict[str, Any]) -> dict[str, Any]:
        prompt = build_prompt(feedback)
        outcome = run_agent(command, prompt, workspace, timeout)
        if outcome["timed_out"]:
            summary = f"Agent stopped after {timeout} s without finishing."
        elif outcome["exit_code"] != 0:
            tail = (outcome["stderr"] or outcome["stdout"]).strip()[-400:]
            summary = f"Agent exited with code {outcome['exit_code']}: {tail}"
        else:
            last = [ln for ln in outcome["stdout"].strip().splitlines() if ln.strip()]
            summary = "Agent finished" + (f": {last[-1][:200]}" if last else ".")
        if on_round:
            on_round({"prompt": prompt, "summary": summary, **outcome})
        return {"improved": outcome["exit_code"] == 0, "summary": summary}

    return repair
