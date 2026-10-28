"""P0-1: judge-generated probes must never FAIL correct code.

Every workspace here is a correct implementation with passing visible tests. The
decision may be PASS or ABSTAIN, never FAIL, and no judge-authored test may fail.
"""

import pytest
from audit_helpers import corpus_workspace, judge, judge_authored_failures, write

ACCEPTANCE = [
    "02_parsing",            # parse_duration: ValueError on ""/"abc"/"1h1h"/"10"
    "01_input_validation",   # validate_age: TypeError for bool/float, ValueError out of range
    "08_merge_intervals",    # merge_intervals(list of tuples)
    "06_decimal_rounding",   # apply_discount with Decimal, ValueError for pct out of range
    "09_ttl_lru_cache",      # TTLCache(capacity, ttl_seconds) evicting at capacity
]


def _assert_not_failed(result):
    assert judge_authored_failures(result) == []
    assert result.decision != "FAIL", result.blocking_issues


@pytest.mark.parametrize("task", ACCEPTANCE)
def test_correct_acceptance_implementation_is_not_failed(tmp_path, task):
    _assert_not_failed(judge(corpus_workspace(tmp_path, task)))


def test_idempotency_probe_treats_validation_error_as_not_applicable(tmp_path):
    ws = write(tmp_path, {
        "phone.py": (
            "def normalize_phone(s: str) -> str:\n"
            "    digits = ''.join(ch for ch in s if ch.isdigit())\n"
            "    if len(digits) != 10:\n"
            "        raise ValueError(f'not a phone number: {s!r}')\n"
            "    return digits\n"
        ),
        "test_phone.py": (
            "from phone import normalize_phone\n"
            "def test_normalize():\n"
            "    assert normalize_phone('(555) 123-4567') == '5551234567'\n"
        ),
    })
    _assert_not_failed(judge(ws))


def test_variance_probe_does_not_flag_validator_that_rejects_all_garbage(tmp_path):
    ws = write(tmp_path, {
        "codes.py": (
            "import re\n"
            "def check_code(code: str) -> str:\n"
            "    if not re.fullmatch(r'[A-Z]{3}-\\d{4}', code):\n"
            "        raise ValueError(f'bad code {code!r}')\n"
            "    return code\n"
        ),
        "test_codes.py": (
            "from codes import check_code\n"
            "def test_ok():\n"
            "    assert check_code('ABC-1234') == 'ABC-1234'\n"
        ),
    })
    _assert_not_failed(judge(ws))


def test_boundary_probe_respects_arity_and_raising(tmp_path):
    ws = write(tmp_path, {
        "limits.py": (
            "def clamp_volume(level: int, step: int) -> int:\n"
            "    if level > 100:\n"
            "        raise ValueError('level above 100')\n"
            "    return min(100, level + step)\n"
            "\n"
            "def describe(level: int) -> str:\n"
            "    return f'level {level}'\n"
        ),
        "test_limits.py": (
            "import pytest\n"
            "from limits import clamp_volume, describe\n"
            "def test_clamp():\n"
            "    assert clamp_volume(95, 10) == 100\n"
            "def test_describe():\n"
            "    assert describe(3) == 'level 3'\n"
            "def test_too_loud():\n"
            "    with pytest.raises(ValueError):\n"
            "        clamp_volume(101, 1)\n"
        ),
    })
    _assert_not_failed(judge(ws))


def test_boundary_probe_does_not_fail_function_returning_none(tmp_path):
    ws = write(tmp_path, {
        "guard.py": (
            "def ensure_positive(n: int) -> None:\n"
            "    if n < 1:\n"
            "        raise ValueError('must be positive')\n"
        ),
        "test_guard.py": (
            "import pytest\n"
            "from guard import ensure_positive\n"
            "def test_ok():\n"
            "    assert ensure_positive(5) is None\n"
            "def test_bad():\n"
            "    with pytest.raises(ValueError):\n"
            "        ensure_positive(0)\n"
        ),
    })
    _assert_not_failed(judge(ws))


def test_unannotated_params_are_not_probed_with_strings(tmp_path):
    ws = write(tmp_path, {
        "mathx.py": (
            "def double(x):\n"
            "    if isinstance(x, str):\n"
            "        raise ValueError('numbers only')\n"
            "    return x * 2\n"
        ),
        "test_mathx.py": (
            "from mathx import double\n"
            "def test_double():\n"
            "    assert double(4) == 8\n"
        ),
    })
    _assert_not_failed(judge(ws))


def test_capacity_probe_skips_unsatisfiable_constructor(tmp_path):
    ws = write(tmp_path, {
        "pool.py": (
            "class Pool:\n"
            "    def __init__(self, capacity, factory):\n"
            "        self.capacity = capacity\n"
            "        self.factory = factory\n"
            "        self.items = []\n"
            "    def add(self, item):\n"
            "        if len(self.items) >= self.capacity:\n"
            "            raise OverflowError('full')\n"
            "        self.items.append(self.factory(item))\n"
        ),
        "test_pool.py": (
            "import pytest\n"
            "from pool import Pool\n"
            "def test_add():\n"
            "    p = Pool(1, str)\n"
            "    p.add(1)\n"
            "    assert p.items == ['1']\n"
            "    with pytest.raises(OverflowError):\n"
            "        p.add(2)\n"
        ),
    })
    _assert_not_failed(judge(ws))


def test_uniqueness_probe_does_not_fail_deterministic_digest(tmp_path):
    ws = write(tmp_path, {
        "digest.py": (
            "import hashlib\n"
            "def fingerprint(data: bytes) -> str:\n"
            "    return hashlib.sha256(data).hexdigest()\n"
        ),
        "test_digest.py": (
            "from digest import fingerprint\n"
            "def test_fingerprint():\n"
            "    assert fingerprint(b'abc').startswith('ba7816bf')\n"
        ),
    })
    _assert_not_failed(judge(ws))


def test_expiration_probe_does_not_rely_on_zero_ttl_and_wall_clock(tmp_path):
    # Correct semantics: an entry is valid while age <= ttl. With ttl=0 and a coarse
    # clock, a fresh entry is legitimately still valid.
    ws = write(tmp_path, {
        "sessions.py": (
            "import time\n"
            "class SessionCache:\n"
            "    def __init__(self, ttl):\n"
            "        self.ttl = ttl\n"
            "        self._items = {}\n"
            "    def put(self, key, value):\n"
            "        self._items[key] = (value, int(time.time()))\n"
            "    def get(self, key):\n"
            "        entry = self._items.get(key)\n"
            "        if entry is None or int(time.time()) - entry[1] > self.ttl:\n"
            "            return None\n"
            "        return entry[0]\n"
        ),
        "test_sessions.py": (
            "from sessions import SessionCache\n"
            "def test_roundtrip():\n"
            "    c = SessionCache(ttl=60)\n"
            "    c.put('a', 1)\n"
            "    assert c.get('a') == 1\n"
        ),
    })
    _assert_not_failed(judge(ws))
