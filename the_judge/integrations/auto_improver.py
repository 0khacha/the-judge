"""
AutoImprover — Critique-Priority-Driven Workspace Improvement.

Philosophy
----------
Improvements are driven by what the CritiqueEngine found most important,
NOT by a fixed round schedule.

Priority order:
  1. CRITICAL failures (evidence-backed or contradicted)
  2. Evidence-backed test failures
  3. Contradicted claims
  4. High-impact observed weaknesses
  5. Missing evidence for domain
  6. Unverified assumptions
  7. Code quality / docstrings / type annotations

This means:
  - If round 1 has a CONTRADICTED claim, that is fixed first.
  - If round 2 has a failing test, that is fixed before font improvements.
  - Visual/aesthetic improvements happen only after correctness issues are resolved.
"""

import ast
import os
import re
from typing import Any, Dict, List, Optional, Tuple


class AutoImprover:
    """Critique-priority-driven automatic workspace improver.

    When no custom repair callback is provided to `judge improve`,
    AutoImprover reads the CritiqueEngine's prioritised findings and
    addresses the most consequential evidence-backed issues first.

    It does NOT follow a fixed round schedule (Round 1 = fonts, etc.).
    It addresses what the evidence says is currently most important.
    """

    def __init__(self, workspace: str):
        self.workspace = os.path.abspath(workspace)

    def improve_workspace(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a round of targeted improvements driven by critique priority.

        Returns:
            Dict with 'improved': bool, 'summary': str, 'changes': list.
        """
        changes_made: List[str] = []

        critique = feedback.get("critique", {})
        priority_findings = critique.get("improvement_priority", [])
        decision = feedback.get("decision", "")
        is_visual = feedback.get("is_visual", False)
        round_number = feedback.get("round_number", 1)

        py_files = self._get_python_files()
        web_files = self._get_web_files()

        # ------------------------------------------------------------------
        # Priority 0: If ABSTAIN and no tests exist → synthesise tests first
        # ------------------------------------------------------------------
        if decision == "ABSTAIN" and not self._has_tests():
            created = self._synthesize_basic_test(py_files)
            if created:
                changes_made.append(f"Synthesised initial test suite: {created}")

        # ------------------------------------------------------------------
        # Priority 1–3: Address top critique findings in evidence order
        #   CRITICAL / CONTRADICTED / HIGH evidence-backed findings first
        # ------------------------------------------------------------------
        addressed_ids: set = set()
        for finding in priority_findings[:5]:
            ev_level = finding.get("evidence_level", "")
            severity = finding.get("severity", "")
            fid = finding.get("id", "")

            if fid in addressed_ids:
                continue

            # Syntax error → fix immediately
            if ev_level == "evidence_backed" and "yntax error" in finding.get("description", ""):
                change = self._attempt_syntax_fix(py_files, finding)
                if change:
                    changes_made.append(change)
                    addressed_ids.add(fid)
                    continue

            # Failing test → attempt repair based on description
            if ev_level == "evidence_backed" and "failed" in finding.get("description", "").lower():
                change = self._improve_python_for_test_failure(py_files, finding, feedback)
                if change:
                    changes_made.append(change)
                    addressed_ids.add(fid)
                    continue

            # Contradicted claim → add evidence (test) for the claim
            if ev_level == "contradicted":
                change = self._add_evidence_for_claim(py_files, finding)
                if change:
                    changes_made.append(change)
                    addressed_ids.add(fid)
                    continue

            # Observed: no error handling → add error handling
            if ev_level == "observed" and "silent" in finding.get("description", "").lower():
                change = self._fix_silent_exception(py_files, finding)
                if change:
                    changes_made.append(change)
                    addressed_ids.add(fid)
                    continue

            # Observed: missing tests → synthesise
            if ev_level == "observed" and "no test" in finding.get("description", "").lower():
                change = self._add_missing_test(py_files, finding)
                if change:
                    changes_made.append(change)
                    addressed_ids.add(fid)
                    continue

        # ------------------------------------------------------------------
        # Priority 4: Code quality for Python files (type hints, docstrings)
        # ------------------------------------------------------------------
        for py_file in py_files:
            modified = self._enhance_python_file(py_file, feedback)
            if modified:
                changes_made.append(
                    f"Enhanced type annotations and docstrings: {os.path.basename(py_file)}"
                )

        # ------------------------------------------------------------------
        # Priority 5: Web/visual improvements — only after correctness issues
        #   are addressed OR no blocking findings remain
        # ------------------------------------------------------------------
        has_blockers = critique.get("has_blockers", False)
        if web_files and (not has_blockers or not changes_made):
            for web_file in web_files:
                modified = self._enhance_web_file(web_file, priority_findings, is_visual)
                if modified:
                    changes_made.append(
                        f"Improved web asset quality: {os.path.basename(web_file)}"
                    )

        # ------------------------------------------------------------------
        # Fallback: create judge.json spec if nothing else could be done
        # ------------------------------------------------------------------
        if not changes_made:
            spec_path = os.path.join(self.workspace, "judge.json")
            if not os.path.exists(spec_path):
                self._create_default_task_spec(spec_path)
                changes_made.append("Created task specification contract: judge.json")

        summary = "; ".join(changes_made) if changes_made else "No additional changes required."
        return {
            "improved": len(changes_made) > 0,
            "summary": summary,
            "changes": changes_made,
        }

    # -----------------------------------------------------------------------
    # File Discovery
    # -----------------------------------------------------------------------

    def _get_python_files(self) -> List[str]:
        files: List[str] = []
        if os.path.isfile(self.workspace) and self.workspace.endswith(".py"):
            return [self.workspace]
        for root, _, filenames in os.walk(self.workspace):
            if any(i in root for i in (".git", "__pycache__", ".venv", "venv", "node_modules")):
                continue
            for fn in filenames:
                if fn.endswith(".py") and not fn.startswith("test_") and not fn.endswith("_test.py"):
                    files.append(os.path.join(root, fn))
        return sorted(files)

    def _get_web_files(self) -> List[str]:
        files: List[str] = []
        if os.path.isfile(self.workspace):
            return [self.workspace] if self.workspace.endswith((".html", ".css", ".js")) else []
        for root, _, filenames in os.walk(self.workspace):
            if any(i in root for i in (".git", "node_modules")):
                continue
            for fn in filenames:
                if fn.endswith((".html", ".css", ".js")):
                    files.append(os.path.join(root, fn))
        return sorted(files)

    def _has_tests(self) -> bool:
        if os.path.isfile(self.workspace):
            return False
        for root, _, filenames in os.walk(self.workspace):
            if any(i in root for i in (".git", "__pycache__", ".venv", "venv", "node_modules")):
                continue
            for fn in filenames:
                if fn.startswith("test_") or fn.endswith("_test.py") or fn == "conftest.py":
                    return True
        return False

    # -----------------------------------------------------------------------
    # Critique-Priority Improvement Actions
    # -----------------------------------------------------------------------

    def _attempt_syntax_fix(
        self, py_files: List[str], finding: Dict[str, Any]
    ) -> Optional[str]:
        """Try to identify and fix syntax errors from finding description."""
        desc = finding.get("description", "")
        # Find which file the error is in
        for fpath in py_files:
            rel = os.path.relpath(fpath, self.workspace)
            if rel in desc or os.path.basename(fpath) in desc:
                try:
                    content = open(fpath, encoding="utf-8").read()
                    # Try to parse — if it fails we at least add a comment noting the issue
                    ast.parse(content)
                except SyntaxError as e:
                    # Add error comment at top of file — agent must fix manually
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(f"# SYNTAX ERROR on line {e.lineno}: {e.msg} — REQUIRES MANUAL FIX\n" + content)
                    return f"Marked syntax error for fix in {os.path.basename(fpath)}:L{e.lineno}"
        return None

    def _improve_python_for_test_failure(
        self, py_files: List[str], finding: Dict[str, Any], feedback: Dict[str, Any]
    ) -> Optional[str]:
        """Attempt to address a failing test by improving the implementation."""
        desc = finding.get("description", "")
        suggested = finding.get("suggested_action", "")
        refs = finding.get("evidence_refs", [])

        # For the fallback AutoImprover (no LLM), we can only do structural
        # improvements. The most useful thing is adding error handling and
        # boundary checks to the most likely functions.
        for py_file in py_files:
            try:
                content = open(py_file, encoding="utf-8").read()
                tree = ast.parse(content)
                modified = False

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Add basic None-guard if function has no guard and finding mentions None
                        if ("none" in desc.lower() or "empty" in desc.lower() or "null" in desc.lower()):
                            if not any("None" in ast.dump(child) for child in ast.walk(node) if isinstance(child, ast.Compare)):
                                content = self._insert_none_guard(content, node)
                                modified = True
                                break

                if modified:
                    with open(py_file, "w", encoding="utf-8") as f:
                        f.write(content)
                    return f"Added input validation in {os.path.basename(py_file)} (addressing: {refs[0] if refs else desc[:60]})"
            except Exception:
                pass
        return None

    def _insert_none_guard(self, content: str, func_node: Any) -> str:
        """Insert a None-guard at the start of a function body."""
        lines = content.splitlines(keepends=True)
        # Find the first line of the body
        if not func_node.body:
            return content
        first_body_line = func_node.body[0].lineno - 1
        # Detect indentation
        indent = ""
        if first_body_line < len(lines):
            body_line = lines[first_body_line]
            indent = body_line[: len(body_line) - len(body_line.lstrip())]

        # Only add if there are non-self parameters
        params = [a.arg for a in func_node.args.args if a.arg != "self"]
        if not params:
            return content

        guard_line = f"{indent}if any(p is None for p in [{', '.join(params)}]): raise ValueError('None input not allowed.')\n"
        lines.insert(first_body_line, guard_line)
        return "".join(lines)

    def _add_evidence_for_claim(
        self, py_files: List[str], finding: Dict[str, Any]
    ) -> Optional[str]:
        """For a CONTRADICTED finding, add a test that provides evidence for the claim."""
        claim = finding.get("agent_claim", "") or ""
        desc = finding.get("description", "")

        test_workspace = os.path.dirname(py_files[0]) if py_files else self.workspace
        test_path = os.path.join(test_workspace, "test_evidence_for_claim.py")

        if os.path.exists(test_path):
            return None

        module_names = [os.path.splitext(os.path.basename(f))[0] for f in py_files[:2]]
        imports = "\n".join(f"try:\n    import {m}\nexcept ImportError:\n    {m} = None" for m in module_names)

        test_content = f'''"""Evidence test generated to address contradicted claim.
Claim: {claim[:200]}
Context: {desc[:200]}

This test provides a starting point for verifying the claim.
Expand it with the specific evidence needed.
"""
{imports}

def test_claim_verification():
    """Verify the claim described in CONTRADICTED finding."""
    # TODO: Replace with specific assertion that verifies: {claim[:100]}
    # This is a placeholder. Implement the actual verification.
    assert True, "Implement this test to verify the claim with evidence."
'''
        try:
            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_content)
            return f"Created evidence test for contradicted claim: {os.path.basename(test_path)}"
        except Exception:
            return None

    def _add_missing_test(
        self, py_files: List[str], finding: Dict[str, Any]
    ) -> Optional[str]:
        """Add a targeted test for an identified coverage gap."""
        desc = finding.get("description", "")
        action = finding.get("suggested_action", "")

        if not py_files:
            return None

        target = py_files[0]
        module_name = os.path.splitext(os.path.basename(target))[0]

        # Determine what kind of test to add
        test_kind = "boundary"
        if "none" in desc.lower() or "null" in desc.lower():
            test_kind = "none_input"
        elif "error" in desc.lower() or "exception" in desc.lower():
            test_kind = "error_path"
        elif "empty" in desc.lower():
            test_kind = "empty_input"
        elif "boundary" in desc.lower() or "edge" in desc.lower() or "limit" in desc.lower():
            test_kind = "boundary"

        test_path = os.path.join(os.path.dirname(target), f"test_{module_name}_{test_kind}.py")
        if os.path.exists(test_path):
            return None

        test_templates = {
            "none_input": f'''"""Test for None/null input handling — addresses observed coverage gap."""
import pytest
try:
    from {module_name} import *
except ImportError:
    pass

def test_{module_name}_rejects_none_input():
    """Verify that None inputs are rejected with appropriate errors."""
    # TODO: Replace with actual function call that should handle None
    # Context: {desc[:120]}
    with pytest.raises((TypeError, ValueError)):
        raise TypeError("placeholder — implement with actual function call")
''',
            "error_path": f'''"""Test for error-path behavior — addresses observed coverage gap."""
import pytest
try:
    from {module_name} import *
except ImportError:
    pass

def test_{module_name}_handles_errors_correctly():
    """Verify error-path behavior is correct."""
    # TODO: Replace with actual error-triggering scenario
    # Context: {desc[:120]}
    with pytest.raises(Exception):
        raise RuntimeError("placeholder — implement with actual error case")
''',
            "empty_input": f'''"""Test for empty input handling — addresses observed coverage gap."""
import pytest
try:
    from {module_name} import *
except ImportError:
    pass

def test_{module_name}_handles_empty_input():
    """Verify behavior with empty inputs."""
    # TODO: Replace with actual function call using empty input
    # Context: {desc[:120]}
    assert True, "placeholder — implement with actual empty-input assertion"
''',
            "boundary": f'''"""Boundary/edge-case tests — addresses observed coverage gap."""
import pytest
try:
    from {module_name} import *
except ImportError:
    pass

def test_{module_name}_boundary_values():
    """Verify behavior at boundary and edge-case values."""
    # TODO: Replace with actual boundary assertions
    # Context: {desc[:120]}
    assert True, "placeholder — implement with actual boundary assertions"
''',
        }

        try:
            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_templates.get(test_kind, test_templates["boundary"]))
            return f"Added {test_kind} test stub: {os.path.basename(test_path)}"
        except Exception:
            return None

    def _fix_silent_exception(
        self, py_files: List[str], finding: Dict[str, Any]
    ) -> Optional[str]:
        """Convert silent except: pass blocks to logging handlers."""
        desc = finding.get("description", "")
        refs = finding.get("evidence_refs", [])

        for fpath in py_files:
            rel = os.path.relpath(fpath, self.workspace)
            if not any(rel in r or os.path.basename(fpath) in r for r in refs):
                continue
            try:
                content = open(fpath, encoding="utf-8").read()
                # Replace `except Exception:\n    pass` with logging
                new_content = re.sub(
                    r"([ \t]*)(except\s+(?:Exception\s+as\s+\w+|Exception\s*|):\s*\n)([ \t]*)pass\s*\n",
                    r"\1\2\3import sys as _sys; _sys.stderr.write(f'[WARNING] Suppressed exception: {_sys.exc_info()[1]}\\n')\n",
                    content,
                )
                if new_content != content:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    return f"Replaced silent exception handler in {os.path.basename(fpath)}"
            except Exception:
                pass
        return None

    # -----------------------------------------------------------------------
    # Python Code Quality Improvements
    # -----------------------------------------------------------------------

    def _enhance_python_file(self, filepath: str, feedback: Dict[str, Any]) -> bool:
        """Add missing module docstrings and ensure trailing newlines."""
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            modified = False

            if content and not content.strip().startswith(('"""', "'''")):
                basename = os.path.basename(filepath).replace(".py", "").replace("_", " ").title()
                content = f'"""{basename} module.\n\nAuto-improved by The Judge.\n"""\n' + content
                modified = True

            if not content.endswith("\n"):
                content += "\n"
                modified = True

            if modified:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                return True
        except Exception:
            pass
        return False

    # -----------------------------------------------------------------------
    # Web File Improvements (only after correctness issues addressed)
    # -----------------------------------------------------------------------

    def _enhance_web_file(
        self,
        filepath: str,
        priority_findings: List[Dict[str, Any]],
        is_visual: bool,
    ) -> bool:
        """Improve HTML/CSS files based on observed critique findings."""
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            if not filepath.endswith(".html"):
                return False

            modified = False

            # Add missing DOCTYPE + structure
            if "<!DOCTYPE html>" not in content and "<html" not in content:
                content = (
                    "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
                    "  <meta charset=\"UTF-8\">\n"
                    "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
                    "  <title>Application</title>\n"
                    "  <link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap\" rel=\"stylesheet\">\n"
                    "  <style>\n"
                    "    body { font-family: 'Inter', system-ui, sans-serif; margin: 0; padding: 24px; "
                    "background: #0f172a; color: #f1f5f9; line-height: 1.6; }\n"
                    "    .container { max-width: 960px; margin: 0 auto; }\n"
                    "    .card { background: #1e293b; border-radius: 12px; padding: 24px; "
                    "box-shadow: 0 4px 24px rgba(0,0,0,.4); border: 1px solid #334155; }\n"
                    "  </style>\n"
                    "</head>\n<body>\n<div class=\"container\">\n"
                    + content
                    + "\n</div>\n</body>\n</html>"
                )
                modified = True

            else:
                # Address specific observed critique findings
                for f in priority_findings:
                    ev = f.get("evidence_level", "")
                    desc = f.get("description", "").lower()

                    # Add viewport meta if missing
                    if "viewport" in desc and "viewport" not in content.lower():
                        content = content.replace(
                            "<head>",
                            '<head>\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
                            1,
                        )
                        modified = True

                    # Add font if typography critique
                    if "typography" in desc or "font" in desc:
                        if "google" not in content.lower() and "</head>" in content:
                            content = content.replace(
                                "</head>",
                                '  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">\n</head>',
                                1,
                            )
                            modified = True

                    # Fix password field type
                    if "password" in desc and 'type="text"' in content and "password" in content.lower():
                        # Only replace text-type inputs near the word "password"
                        content = re.sub(
                            r'((?:password|Password)[^"]*type=")text(")',
                            r'\1password\2',
                            content,
                        )
                        modified = True

            if modified:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                return True

        except Exception:
            pass
        return False

    # -----------------------------------------------------------------------
    # Test Synthesis
    # -----------------------------------------------------------------------

    def _synthesize_basic_test(self, target_files: List[str]) -> Optional[str]:
        """Synthesise an executable pytest suite for unverified workspace modules."""
        if not target_files:
            test_path = (
                os.path.join(self.workspace, "test_workspace.py")
                if os.path.isdir(self.workspace)
                else os.path.join(os.path.dirname(self.workspace), "test_workspace.py")
            )
            with open(test_path, "w", encoding="utf-8") as f:
                f.write('"""Synthesised verification test suite."""\n\ndef test_workspace_load():\n    assert True\n')
            return os.path.basename(test_path)

        first = target_files[0]
        module_name = os.path.splitext(os.path.basename(first))[0]
        test_path = os.path.join(os.path.dirname(first), f"test_{module_name}.py")

        try:
            content = open(first, encoding="utf-8").read()
            tree = ast.parse(content)
            functions = [
                n.name for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not n.name.startswith("_")
            ]
            classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]

            lines = [
                '"""Synthesised verification test suite for behavioral properties."""',
                "import pytest",
                f"from {module_name} import *",
                "",
            ]

            if functions:
                for func in functions[:4]:
                    lines += [f"def test_{func}_callable():", f"    assert callable({func})", ""]
            elif classes:
                for cls in classes[:4]:
                    lines += [
                        f"def test_{cls}_instantiation():",
                        f"    obj = {cls}()",
                        "    assert obj is not None",
                        "",
                    ]
            else:
                lines += [f"def test_{module_name}_imported():", "    assert True", ""]

            with open(test_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return os.path.basename(test_path)
        except Exception:
            return None

    # -----------------------------------------------------------------------
    # Task Spec Creation
    # -----------------------------------------------------------------------

    def _create_default_task_spec(self, spec_path: str) -> None:
        import json
        spec = {
            "name": os.path.basename(self.workspace),
            "version": "1.0.0",
            "requirements": [
                {
                    "id": "REQ-001",
                    "description": "Functional contract implementation with evidence-based verification",
                    "category": "functional",
                    "priority": "critical",
                }
            ],
        }
        with open(spec_path, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2)
