"""Requirement checklist: every rule in the task spec needs a test.

Mutation feedback finds code no test checks; it cannot find behaviour the code does not
have at all. The checklist does: the judge numbers the rules of TASK.md / SPEC.md /
REQUIREMENTS.md (R1..Rn) and requires each one to be covered by a passing test whose
source mentions its id. `judge freeze` already reports uncovered rules, so the agent
can write those tests before the implementation, where they count as independent.
"""

from audit_helpers import write
from the_judge.api import freeze, verify
from the_judge.core.checklist import covered_ids, extract_requirements

SPEC = """# Task: grades

Create `grade.py` with `grade(score)`.

Rules:
- 90 to 100 gives "A", 80 to 89 gives "B", 0 to 79 gives "C".
- A score outside 0..100 raises `ValueError`.
1. A non-integer score raises `TypeError`.

```python
- this bullet is inside a code block and is not a rule
```
- ok
"""
CORRECT = '''
def grade(score):
    if not isinstance(score, int) or isinstance(score, bool):
        raise TypeError(score)
    if score < 0 or score > 100:
        raise ValueError(score)
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    return "C"
'''
NO_TYPE_CHECK = CORRECT.replace(
    "    if not isinstance(score, int) or isinstance(score, bool):\n        raise TypeError(score)\n", "")
TESTS_R1_R2 = '''
import pytest
from grade import grade


def test_bands():  # R1
    assert grade(95) == "A"
    assert grade(90) == "A"
    assert grade(89) == "B"
    assert grade(80) == "B"
    assert grade(79) == "C"
    assert grade(0) == "C"


def test_range():
    """R2: outside 0..100 raises."""
    with pytest.raises(ValueError):
        grade(-1)
    with pytest.raises(ValueError):
        grade(101)
'''
TEST_R3 = '''
import pytest
from grade import grade


@pytest.mark.parametrize("bad", [1.5, "90", None])  # R3
def test_type(bad):
    with pytest.raises(TypeError):
        grade(bad)
'''


def ws_with(tmp_path, tests, impl, spec=SPEC):
    ws = write(tmp_path, {"TASK.md": spec, **tests})
    freeze(ws)
    write(ws, {"grade.py": impl})
    return ws


def test_extracts_list_items_outside_code_blocks():
    reqs = extract_requirements(SPEC)
    assert [r["id"] for r in reqs] == ["R1", "R2", "R3"]
    assert "outside 0..100" in reqs[1]["text"]
    assert all("code block" not in r["text"] for r in reqs)


def test_coverage_from_comment_docstring_and_decorator():
    tests = {"test_a.py": TESTS_R1_R2, "test_b.py": TEST_R3}
    assert covered_ids(tests) == {"R1": ["test_bands"], "R2": ["test_range"], "R3": ["test_type"]}


def test_r1_does_not_cover_r10():
    assert covered_ids({"t.py": "def test_x():  # R10\n    assert 1\n"}) == {"R10": ["test_x"]}


def test_freeze_reports_uncovered_requirements(tmp_path):
    ws = write(tmp_path, {"TASK.md": SPEC, "test_grade.py": TESTS_R1_R2})
    info = freeze(ws)
    assert [r["id"] for r in info["requirements"]] == ["R1", "R2", "R3"]
    assert info["uncovered_requirements"] == ["R3"]


def test_uncovered_requirement_withholds_pass(tmp_path):
    result = verify(str(ws_with(tmp_path, {"test_grade.py": TESTS_R1_R2}, CORRECT)), mutation=False)
    assert result.decision == "ABSTAIN"
    first = result.next_actions[0]
    assert first["action"] == "cover_requirement"
    assert "R3" in first["detail"] and "TypeError" in first["detail"]
    assert any(f.category == "requirements" for f in result.findings)


def test_all_requirements_covered_passes(tmp_path):
    tests = {"test_grade.py": TESTS_R1_R2, "test_types.py": TEST_R3}
    result = verify(str(ws_with(tmp_path, tests, CORRECT)), mutation=False)
    assert result.decision == "PASS", result.next_actions
    assert result.trust_profile["requirements_checklist"]["uncovered"] == []


def test_failing_test_does_not_cover_its_requirement(tmp_path):
    tests = {"test_grade.py": TESTS_R1_R2, "test_types.py": TEST_R3}
    result = verify(str(ws_with(tmp_path, tests, NO_TYPE_CHECK)), mutation=False)
    assert result.decision == "FAIL"


def test_rule_deleted_from_spec_after_freeze_is_still_required(tmp_path):
    ws = ws_with(tmp_path, {"test_grade.py": TESTS_R1_R2}, CORRECT)
    write(ws, {"TASK.md": SPEC.replace("1. A non-integer score raises `TypeError`.\n", "")})
    result = verify(str(ws), mutation=False)
    assert result.decision == "ABSTAIN"
    assert "R3" in result.next_actions[0]["detail"]


def test_workspace_without_spec_is_unaffected(tmp_path):
    ws = write(tmp_path, {"test_grade.py": TESTS_R1_R2})
    freeze(ws)
    write(ws, {"grade.py": CORRECT})
    assert verify(str(ws), mutation=False).decision == "PASS"


def test_checklist_can_be_disabled(tmp_path):
    ws = ws_with(tmp_path, {"test_grade.py": TESTS_R1_R2}, CORRECT)
    assert verify(str(ws), mutation=False, requirements=False).decision == "PASS"


def test_improve_loop_uncovered_rule_test_reveals_missing_behaviour(tmp_path):
    """The omission mutation cannot see: the code has no type check at all. The
    checklist names R3, the agent's test for it fails, the fix gives PASS."""
    ws = ws_with(tmp_path, {"test_grade.py": TESTS_R1_R2}, NO_TYPE_CHECK)
    first = verify(str(ws), mutation=False, record_history=True)
    assert first.decision == "ABSTAIN" and first.next_actions[0]["action"] == "cover_requirement"

    write(ws, {"test_types.py": TEST_R3})
    second = verify(str(ws), mutation=False, record_history=True)
    assert second.decision == "FAIL" and second.next_actions[0]["action"] == "fix_code"

    write(ws, {"grade.py": CORRECT})
    third = verify(str(ws), mutation=False, record_history=True)
    assert third.decision == "PASS", third.next_actions
