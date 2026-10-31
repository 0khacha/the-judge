"""Writes the 5 benchmark tasks. Public part -> eval_results/tasks, secret part -> hidden dir."""
import os
import sys
import textwrap

PUBLIC = sys.argv[1]
HIDDEN = sys.argv[2]


def w(base, rel, text):
    path = os.path.join(base, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(textwrap.dedent(text).lstrip("\n"))


# ---------------------------------------------------------------- T1 parser
T = "T1_query_parser"
w(PUBLIC, f"{T}/TASK.md", '''
    # Task: query-string parser

    Create `querystring.py` with a function:

        parse_query(qs: str) -> dict[str, list[str]]

    Parse a URL query string into a dict mapping each key to the list of its values.

    - A single leading `?` is ignored.
    - Pairs are separated by `&`; empty segments (e.g. from `&&`) are ignored.
    - Each pair is split on the FIRST `=`. A segment without `=` is a key with value `""`.
    - In keys and values, `+` means a space, and `%XX` percent-escapes are decoded as UTF-8.
      An invalid escape (such as `%zz` or a trailing `%4`) is kept literally.
    - Repeated keys collect their values in order. Keys appear in first-seen order.

    Examples (also in `test_visible.py`):

        parse_query("a=1&b=2")         == {"a": ["1"], "b": ["2"]}
        parse_query("a=1&a=2")         == {"a": ["1", "2"]}
        parse_query("name=John+Smith") == {"name": ["John Smith"]}
''')
w(PUBLIC, f"{T}/test_visible.py", '''
    from querystring import parse_query


    def test_simple():
        assert parse_query("a=1&b=2") == {"a": ["1"], "b": ["2"]}


    def test_repeated_key():
        assert parse_query("a=1&a=2") == {"a": ["1", "2"]}


    def test_plus_is_space():
        assert parse_query("name=John+Smith") == {"name": ["John Smith"]}
''')
w(HIDDEN, f"{T}/test_hidden.py", '''
    import pytest

    from querystring import parse_query


    @pytest.mark.parametrize("qs,expected", [
        ("a=1&b=2", {"a": ["1"], "b": ["2"]}),
        ("", {}),
        ("?", {}),
        ("?a=1", {"a": ["1"]}),
        ("a&b=", {"a": [""], "b": [""]}),
        ("a=b=c", {"a": ["b=c"]}),
        ("&&a=1&&", {"a": ["1"]}),
        ("%E2%9C%93=ok", {"\\u2713": ["ok"]}),
        ("x=%zz", {"x": ["%zz"]}),
        ("x=%4", {"x": ["%4"]}),
        ("x=%2B1", {"x": ["+1"]}),
        ("+k+=+v+", {" k ": [" v "]}),
        ("caf%C3%A9=1", {"caf\\u00e9": ["1"]}),
    ])
    def test_cases(qs, expected):
        assert parse_query(qs) == expected


    def test_key_order_is_first_seen():
        assert list(parse_query("b=1&a=2&b=3")) == ["b", "a"]
        assert parse_query("b=1&a=2&b=3")["b"] == ["1", "3"]
''')
w(HIDDEN, f"{T}/reference.py", '''
    from urllib.parse import unquote


    def _decode(s):
        return unquote(s.replace("+", " "), encoding="utf-8", errors="strict")


    def parse_query(qs: str) -> dict:
        if qs.startswith("?"):
            qs = qs[1:]
        out = {}
        for seg in qs.split("&"):
            if not seg:
                continue
            key, _, value = seg.partition("=")
            out.setdefault(_decode(key), []).append(_decode(value))
        return out
''')
w(HIDDEN, f"{T}/broken.py", '''
    from urllib.parse import parse_qs


    def parse_query(qs: str) -> dict:
        # Subtle bug: parse_qs drops blank values ("a&b=") by default.
        return parse_qs(qs.lstrip("?"))
''')

# ---------------------------------------------------------------- T2 rate limiter
T = "T2_rate_limiter"
w(PUBLIC, f"{T}/TASK.md", '''
    # Task: sliding-window rate limiter

    Create `ratelimit.py` with a class:

        RateLimiter(max_calls: int, period: float, clock=time.monotonic)
            .allow(key: str) -> bool
            .remaining(key: str) -> int

    - `allow(key)` returns True and records the call if fewer than `max_calls` calls for that
      key were ALLOWED during the last `period` seconds, otherwise returns False.
      "During the last period seconds" means with a timestamp `t` such that `now - period < t`.
    - Rejected calls are not recorded and do not count.
    - Keys are independent.
    - `remaining(key)` returns how many more calls would be allowed right now (it does not
      record anything).
    - `clock` is a zero-argument callable returning the current time in seconds.
    - `max_calls < 1` or `period <= 0` raises ValueError.

    Example (also in `test_visible.py`): with `RateLimiter(2, 10)`, `allow("a")` returns
    True, True, then False; `allow("b")` is still True.
''')
w(PUBLIC, f"{T}/test_visible.py", '''
    from ratelimit import RateLimiter


    def test_limit_reached():
        rl = RateLimiter(2, 10)
        assert rl.allow("a") is True
        assert rl.allow("a") is True
        assert rl.allow("a") is False


    def test_keys_independent():
        rl = RateLimiter(1, 10)
        assert rl.allow("a") is True
        assert rl.allow("b") is True
''')
w(HIDDEN, f"{T}/test_hidden.py", '''
    import pytest

    from ratelimit import RateLimiter


    class Clock:
        def __init__(self):
            self.t = 1000.0

        def __call__(self):
            return self.t


    def make(max_calls=2, period=10.0):
        c = Clock()
        return RateLimiter(max_calls, period, clock=c), c


    def test_basic_limit():
        rl, c = make()
        assert [rl.allow("a") for _ in range(3)] == [True, True, False]


    def test_window_slides_not_fixed():
        rl, c = make(2, 10.0)
        c.t = 1000.0; assert rl.allow("k")
        c.t = 1009.0; assert rl.allow("k")
        c.t = 1011.0; assert rl.allow("k")       # window (1001, 1011] holds only 1009
        c.t = 1012.0; assert not rl.allow("k")   # holds 1009 and 1011
        c.t = 1019.5; assert rl.allow("k")       # 1009 has left the window


    def test_boundary_is_exclusive():
        rl, c = make(1, 10.0)
        assert rl.allow("k")
        c.t += 10.0
        assert rl.allow("k")


    def test_rejected_calls_do_not_count():
        rl, c = make(1, 10.0)
        assert rl.allow("k")
        c.t += 5; assert not rl.allow("k")
        c.t += 5.5; assert rl.allow("k")


    def test_remaining():
        rl, c = make(3, 10.0)
        assert rl.remaining("k") == 3
        rl.allow("k"); rl.allow("k")
        assert rl.remaining("k") == 1
        assert rl.remaining("k") == 1  # does not record
        c.t += 11
        assert rl.remaining("k") == 3


    @pytest.mark.parametrize("args", [(0, 10), (-1, 10), (1, 0), (1, -5)])
    def test_invalid(args):
        with pytest.raises(ValueError):
            RateLimiter(*args)
''')
w(HIDDEN, f"{T}/reference.py", '''
    import time
    from collections import defaultdict, deque


    class RateLimiter:
        def __init__(self, max_calls: int, period: float, clock=time.monotonic):
            if max_calls < 1 or period <= 0:
                raise ValueError("max_calls must be >= 1 and period > 0")
            self.max_calls = max_calls
            self.period = period
            self._clock = clock
            self._calls = defaultdict(deque)

        def _prune(self, key, now):
            q = self._calls[key]
            while q and not (now - self.period < q[0]):
                q.popleft()
            return q

        def allow(self, key: str) -> bool:
            now = self._clock()
            q = self._prune(key, now)
            if len(q) < self.max_calls:
                q.append(now)
                return True
            return False

        def remaining(self, key: str) -> int:
            return self.max_calls - len(self._prune(key, self._clock()))
''')
w(HIDDEN, f"{T}/broken.py", '''
    import time


    class RateLimiter:
        """Subtle bug: fixed windows aligned to multiples of period."""

        def __init__(self, max_calls: int, period: float, clock=time.monotonic):
            if max_calls < 1 or period <= 0:
                raise ValueError("bad args")
            self.max_calls, self.period, self._clock = max_calls, period, clock
            self._counts = {}

        def _bucket(self, key):
            window = int(self._clock() // self.period)
            w, n = self._counts.get(key, (window, 0))
            return (window, 0) if w != window else (w, n)

        def allow(self, key: str) -> bool:
            w, n = self._bucket(key)
            if n < self.max_calls:
                self._counts[key] = (w, n + 1)
                return True
            return False

        def remaining(self, key: str) -> int:
            return self.max_calls - self._bucket(key)[1]
''')

# ---------------------------------------------------------------- T3 slugify
T = "T3_slugify"
w(PUBLIC, f"{T}/TASK.md", '''
    # Task: slugify

    Create `slug.py` with a function:

        slugify(text: str, max_length: int | None = None) -> str

    - Normalise with Unicode NFKD and drop every character that is not ASCII afterwards
      (so "é" becomes "e"; characters with no ASCII decomposition are removed).
    - Lower-case.
    - Every run of characters that are not ASCII letters or digits becomes a single `-`.
    - No leading or trailing `-`. Input with no letters or digits gives `""`.
    - If `max_length` is given, the result has at most `max_length` characters. Cut at a `-`
      boundary so no word is split, keeping as many whole words as fit; if even the first
      word is longer than `max_length`, cut that word to `max_length` characters. Never end
      with `-`.
    - `max_length < 1` raises ValueError.

    Examples (also in `test_visible.py`):

        slugify("Hello World")  == "hello-world"
        slugify("Café au lait") == "cafe-au-lait"
''')
w(PUBLIC, f"{T}/test_visible.py", '''
    from slug import slugify


    def test_basic():
        assert slugify("Hello World") == "hello-world"


    def test_accents():
        assert slugify("Caf\\u00e9 au lait") == "cafe-au-lait"
''')
w(HIDDEN, f"{T}/test_hidden.py", '''
    import pytest

    from slug import slugify


    @pytest.mark.parametrize("text,expected", [
        ("Hello World", "hello-world"),
        ("", ""),
        ("!!!", ""),
        ("  --Hello--  ", "hello"),
        ("\\u00c5ngstr\\u00f6m", "angstrom"),
        ("\\u65e5\\u672c\\u8a9e text", "text"),
        ("a_b", "a-b"),
        ("Version 2.0", "version-2-0"),
        ("\\ufb01ne", "fine"),
        ("A  &  B", "a-b"),
    ])
    def test_slugify(text, expected):
        assert slugify(text) == expected


    @pytest.mark.parametrize("text,n,expected", [
        ("hello world foo", 11, "hello-world"),
        ("hello world foo", 12, "hello-world"),
        ("hello world", 5, "hello"),
        ("hello world", 7, "hello"),
        ("supercalifragilistic", 5, "super"),
        ("a b", 2, "a"),
        ("a b", 3, "a-b"),
        ("hello", 100, "hello"),
    ])
    def test_max_length(text, n, expected):
        result = slugify(text, n)
        assert result == expected
        assert len(result) <= n and not result.endswith("-")


    @pytest.mark.parametrize("n", [0, -1])
    def test_invalid_max_length(n):
        with pytest.raises(ValueError):
            slugify("abc", n)
''')
w(HIDDEN, f"{T}/reference.py", '''
    import re
    import unicodedata


    def slugify(text: str, max_length=None) -> str:
        if max_length is not None and max_length < 1:
            raise ValueError("max_length must be >= 1")
        ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
        if max_length is None or len(slug) <= max_length:
            return slug
        cut = slug[:max_length + 1]
        if "-" in cut:
            return cut[:cut.rindex("-")].rstrip("-")
        return slug[:max_length]
''')
w(HIDDEN, f"{T}/broken.py", '''
    import re
    import unicodedata


    def slugify(text: str, max_length=None) -> str:
        if max_length is not None and max_length < 1:
            raise ValueError("max_length must be >= 1")
        ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
        # Subtle bug: hard cut can split a word and leave a trailing "-".
        return slug if max_length is None else slug[:max_length]
''')

# ---------------------------------------------------------------- T4 parallel_map
T = "T4_parallel_map"
w(PUBLIC, f"{T}/TASK.md", '''
    # Task: ordered parallel map

    Create `pmap.py` with a function:

        parallel_map(fn, items, workers: int = 4) -> list

    - Apply `fn` to every item using threads, with at most `workers` calls running at the
      same time, and actually running up to `workers` calls concurrently.
    - Return the results in the same order as the input items.
    - `items` can be any iterable, including a generator. Empty input returns `[]`.
    - `workers < 1` raises ValueError.
    - If `fn` raises for one or more items, `parallel_map` raises the exception raised for the
      item that comes EARLIEST in the input order.

    Examples (also in `test_visible.py`):

        parallel_map(lambda x: x * x, [1, 2, 3]) == [1, 4, 9]
        parallel_map(str, []) == []
''')
w(PUBLIC, f"{T}/test_visible.py", '''
    from pmap import parallel_map


    def test_squares():
        assert parallel_map(lambda x: x * x, [1, 2, 3]) == [1, 4, 9]


    def test_empty():
        assert parallel_map(str, []) == []
''')
w(HIDDEN, f"{T}/test_hidden.py", '''
    import threading
    import time

    import pytest

    from pmap import parallel_map


    def test_order_with_uneven_durations():
        def slow(x):
            time.sleep(0.05 * (5 - x))
            return x * 10
        assert parallel_map(slow, range(5), workers=5) == [0, 10, 20, 30, 40]


    def test_generator_input():
        assert parallel_map(lambda x: x + 1, (i for i in range(10)), workers=3) == list(range(1, 11))


    def test_runs_concurrently():
        start = time.monotonic()
        parallel_map(lambda _: time.sleep(0.3), range(4), workers=4)
        assert time.monotonic() - start < 0.9


    def test_never_exceeds_workers():
        lock = threading.Lock()
        state = {"now": 0, "peak": 0}

        def fn(_):
            with lock:
                state["now"] += 1
                state["peak"] = max(state["peak"], state["now"])
            time.sleep(0.05)
            with lock:
                state["now"] -= 1
        parallel_map(fn, range(12), workers=3)
        assert state["peak"] <= 3
        assert state["peak"] >= 2


    def test_earliest_exception_wins():
        def fn(i):
            if i == 1:
                time.sleep(0.3)
                raise KeyError("first")
            if i == 3:
                time.sleep(0.01)
                raise ValueError("later")
            return i
        with pytest.raises(KeyError):
            parallel_map(fn, range(5), workers=5)


    def test_empty_and_more_workers_than_items():
        assert parallel_map(str, [], workers=8) == []
        assert parallel_map(str, [1], workers=8) == ["1"]


    @pytest.mark.parametrize("w", [0, -2])
    def test_invalid_workers(w):
        with pytest.raises(ValueError):
            parallel_map(str, [1], workers=w)
''')
w(HIDDEN, f"{T}/reference.py", '''
    from concurrent.futures import ThreadPoolExecutor


    def parallel_map(fn, items, workers: int = 4) -> list:
        if workers < 1:
            raise ValueError("workers must be >= 1")
        items = list(items)
        if not items:
            return []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(fn, item) for item in items]
        return [f.result() for f in futures]
''')
w(HIDDEN, f"{T}/broken.py", '''
    from concurrent.futures import ThreadPoolExecutor, as_completed


    def parallel_map(fn, items, workers: int = 4) -> list:
        if workers < 1:
            raise ValueError("workers must be >= 1")
        items = list(items)
        results = [None] * len(items)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(fn, item): i for i, item in enumerate(items)}
            # Subtle bug: raises whichever exception finishes first, not the earliest item's.
            for f in as_completed(futures):
                results[futures[f]] = f.result()
        return results
''')

# ---------------------------------------------------------------- T5 split_bill (trap)
T = "T5_split_bill"
w(PUBLIC, f"{T}/TASK.md", '''
    # Task: split a bill

    Create `bill.py` with a function:

        split_bill(total_cents: int, n: int) -> list[int]

    Split `total_cents` between `n` people as whole cents.

    - The shares sum exactly to `total_cents`.
    - Any two shares differ by at most 1 cent.
    - Larger shares come first.
    - `total_cents == 0` gives `n` zeros.
    - `n < 1` or `total_cents < 0` raises ValueError.

    Examples (also in `test_visible.py`):

        split_bill(1000, 4) == [250, 250, 250, 250]
        split_bill(900, 3)  == [300, 300, 300]
''')
w(PUBLIC, f"{T}/test_visible.py", '''
    from bill import split_bill


    def test_even_four():
        assert split_bill(1000, 4) == [250, 250, 250, 250]


    def test_even_three():
        assert split_bill(900, 3) == [300, 300, 300]
''')
w(HIDDEN, f"{T}/test_hidden.py", '''
    import pytest

    from bill import split_bill


    @pytest.mark.parametrize("total,n,expected", [
        (1000, 4, [250, 250, 250, 250]),
        (1000, 3, [334, 333, 333]),
        (1, 3, [1, 0, 0]),
        (0, 2, [0, 0]),
        (7, 7, [1] * 7),
        (10, 1, [10]),
        (11, 4, [3, 3, 3, 2]),
    ])
    def test_split(total, n, expected):
        assert split_bill(total, n) == expected


    @pytest.mark.parametrize("total,n", [(10**6 + 7, 13), (99, 100), (12345, 7)])
    def test_invariants(total, n):
        shares = split_bill(total, n)
        assert len(shares) == n and sum(shares) == total
        assert max(shares) - min(shares) <= 1
        assert shares == sorted(shares, reverse=True)


    @pytest.mark.parametrize("total,n", [(10, 0), (10, -1), (-1, 2)])
    def test_invalid(total, n):
        with pytest.raises(ValueError):
            split_bill(total, n)
''')
w(HIDDEN, f"{T}/reference.py", '''
    def split_bill(total_cents: int, n: int) -> list:
        if n < 1 or total_cents < 0:
            raise ValueError("n must be >= 1 and total_cents >= 0")
        base, extra = divmod(total_cents, n)
        return [base + 1] * extra + [base] * (n - extra)
''')
w(HIDDEN, f"{T}/broken.py", '''
    def split_bill(total_cents: int, n: int) -> list:
        if n < 1 or total_cents < 0:
            raise ValueError("n must be >= 1 and total_cents >= 0")
        # The obvious solution: passes the visible examples, loses the remainder.
        return [total_cents // n] * n
''')
print("ok")
