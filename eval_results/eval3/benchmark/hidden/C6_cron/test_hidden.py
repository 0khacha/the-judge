from datetime import datetime, date, timezone

import pytest
from cron import next_run, next_runs

D = datetime


@pytest.mark.parametrize("expr,after,exp", [
    ("*/15 * * * *", D(2024, 1, 1, 10, 7), D(2024, 1, 1, 10, 15)),
    ("*/15 * * * *", D(2024, 1, 1, 10, 15), D(2024, 1, 1, 10, 30)),
    ("*/15 * * * *", D(2024, 1, 1, 10, 15, 30), D(2024, 1, 1, 10, 30)),
    ("*/15 * * * *", D(2024, 1, 1, 10, 45), D(2024, 1, 1, 11, 0)),
    ("*/15 * * * *", D(2024, 1, 1, 23, 50), D(2024, 1, 2, 0, 0)),
    ("* * * * *", D(2024, 1, 1, 10, 0, 0), D(2024, 1, 1, 10, 1)),
    ("* * * * *", D(2024, 1, 1, 10, 0, 59, 999999), D(2024, 1, 1, 10, 1)),
    ("* * * * *", D(2024, 12, 31, 23, 59), D(2025, 1, 1, 0, 0)),
    ("30 10 * * *", D(2024, 1, 1, 10, 30), D(2024, 1, 2, 10, 30)),
    ("30 10 * * *", D(2024, 1, 1, 10, 29, 59), D(2024, 1, 1, 10, 30)),
    ("59 23 31 12 *", D(2024, 12, 31, 23, 59), D(2025, 12, 31, 23, 59)),
    ("30,0 8,7 * * *", D(2024, 1, 1, 0, 0), D(2024, 1, 1, 7, 0)),
])
def test_basic_search(expr, after, exp):
    r = next_run(expr, after)
    assert r == exp
    assert r.second == 0 and r.microsecond == 0
    assert r > after


@pytest.mark.parametrize("expr,after,exp", [
    ("0 9 * * 1-5", D(2024, 3, 1, 10, 0), D(2024, 3, 4, 9, 0)),
    ("0 9 * * 1-5", D(2024, 3, 4, 8, 0), D(2024, 3, 4, 9, 0)),
    ("0 9 * * 1-5", D(2024, 3, 3, 12, 0), D(2024, 3, 4, 9, 0)),
    ("0 0 * * 7", D(2024, 1, 1, 0, 0), D(2024, 1, 7, 0, 0)),
    ("0 0 * * 0", D(2024, 1, 1, 0, 0), D(2024, 1, 7, 0, 0)),
    ("0 0 * * sun", D(2024, 1, 1, 0, 0), D(2024, 1, 7, 0, 0)),
    ("0 0 * * SAT", D(2024, 1, 1, 0, 0), D(2024, 1, 6, 0, 0)),
    ("0 0 * * mon-fri", D(2024, 3, 1, 0, 0), D(2024, 3, 4, 0, 0)),
    ("0 0 * * Mon-Fri/2", D(2024, 1, 1, 0, 0), D(2024, 1, 3, 0, 0)),
    ("0 0 * * */2", D(2024, 1, 1, 0, 0), D(2024, 1, 2, 0, 0)),
])
def test_day_of_week(expr, after, exp):
    assert next_run(expr, after) == exp


def test_dow_range_ending_in_7():
    assert next_runs("0 0 * * 5-7", D(2024, 1, 1, 0, 0), 3) == [D(2024, 1, 5), D(2024, 1, 6), D(2024, 1, 7)]


@pytest.mark.parametrize("expr,after,exp", [
    ("30 2 29 2 *", D(2023, 1, 1), D(2024, 2, 29, 2, 30)),
    ("30 2 29 2 *", D(2024, 2, 29, 2, 30), D(2028, 2, 29, 2, 30)),
    ("0 0 29 2 *", D(2096, 3, 1), D(2104, 2, 29)),
    ("0 0 29 2 *", D(2100, 1, 1), D(2104, 2, 29)),
    ("0 0 31 * *", D(2024, 4, 15), D(2024, 5, 31)),
    ("0 0 31 * *", D(2024, 1, 31, 0, 0), D(2024, 3, 31)),
    ("0 0 1 jan,JUL *", D(2024, 1, 1, 0, 0), D(2024, 7, 1)),
    ("0 0 1 jan-mar *", D(2024, 3, 1, 0, 0), D(2025, 1, 1)),
    ("0 0 1 * *", D(2024, 12, 15), D(2025, 1, 1)),
])
def test_calendar(expr, after, exp):
    assert next_run(expr, after) == exp


def test_dom_or_dow_when_both_restricted():
    # 2024-01-01 is a Monday; 13th is a Saturday
    got = next_runs("0 0 13 * 5", D(2024, 1, 1, 0, 0), 4)
    assert got == [D(2024, 1, 5), D(2024, 1, 12), D(2024, 1, 13), D(2024, 1, 19)]


def test_dom_or_dow_full_range_is_restricted():
    assert next_run("0 0 1-31 * 1", D(2024, 1, 1, 0, 0)) == D(2024, 1, 2, 0, 0)
    assert next_run("0 0 1 * 1", D(2024, 1, 1, 0, 0)) == D(2024, 1, 8, 0, 0)


def test_star_step_dom_is_unrestricted_and():
    assert next_runs("0 0 */2 * 1", D(2024, 1, 1, 0, 0), 2) == [D(2024, 1, 15), D(2024, 1, 29)]
    assert next_run("0 0 */2 * 1-5", D(2024, 1, 1, 0, 0)) == D(2024, 1, 3, 0, 0)


def test_dom_restricted_dow_star_is_and():
    assert next_run("0 0 15 * *", D(2024, 1, 15, 0, 0)) == D(2024, 2, 15, 0, 0)
    assert next_run("0 0 * * 1", D(2024, 1, 1, 0, 0)) == D(2024, 1, 8, 0, 0)


@pytest.mark.parametrize("expr,after,exp", [
    ("0-30/10 * * * *", D(2024, 1, 1, 10, 30), D(2024, 1, 1, 11, 0)),
    ("0-30/10 * * * *", D(2024, 1, 1, 10, 5), D(2024, 1, 1, 10, 10)),
    ("10-30/10 * * * *", D(2024, 1, 1, 10, 20), D(2024, 1, 1, 10, 30)),
    ("5/20 * * * *", D(2024, 1, 1, 10, 5), D(2024, 1, 1, 10, 25)),
    ("5/20 * * * *", D(2024, 1, 1, 10, 45), D(2024, 1, 1, 11, 5)),
    ("*/20 * * * *", D(2024, 1, 1, 10, 40), D(2024, 1, 1, 11, 0)),
    ("0 8,17 * * *", D(2024, 1, 1, 9, 0), D(2024, 1, 1, 17, 0)),
    ("0 8,17 * * *", D(2024, 1, 1, 17, 0), D(2024, 1, 2, 8, 0)),
    ("05 * * * *", D(2024, 1, 1, 10, 0), D(2024, 1, 1, 10, 5)),
    ("0 09 * * *", D(2024, 1, 1, 0, 0), D(2024, 1, 1, 9, 0)),
    ("  0   12  * *  *  ", D(2024, 1, 1, 0, 0), D(2024, 1, 1, 12, 0)),
    ("0\t12 * * *", D(2024, 1, 1, 0, 0), D(2024, 1, 1, 12, 0)),
    ("0 */6 * * *", D(2024, 1, 1, 6, 0), D(2024, 1, 1, 12, 0)),
])
def test_steps_lists_whitespace(expr, after, exp):
    assert next_run(expr, after) == exp


@pytest.mark.parametrize("expr,exp", [
    ("@daily", D(2024, 5, 6, 0, 0)),
    ("@midnight", D(2024, 5, 6, 0, 0)),
    ("@hourly", D(2024, 5, 5, 14, 0)),
    ("@weekly", D(2024, 5, 12, 0, 0)),
    ("@monthly", D(2024, 6, 1, 0, 0)),
    ("@yearly", D(2025, 1, 1, 0, 0)),
    ("@annually", D(2025, 1, 1, 0, 0)),
])
def test_aliases(expr, exp):
    assert next_run(expr, D(2024, 5, 5, 13, 0)) == exp


@pytest.mark.parametrize("expr", ["@reboot", "@DAILY", "@", "@daily *", "@every"])
def test_bad_aliases(expr):
    with pytest.raises(ValueError):
        next_run(expr, D(2024, 1, 1))


@pytest.mark.parametrize("expr", [
    "* * * *", "* * * * * *", "", "   ", "60 * * * *", "* 24 * * *", "* * 0 * *", "* * 32 * *",
    "* * * 0 *", "* * * 13 *", "* * * * 8", "*/0 * * * *", "5-1 * * * *", "a * * * *",
    "1,,2 * * * *", "1, * * * *", ",1 * * * *", "-5 * * * *", "*/-1 * * * *", "*/x * * * *",
    "1-2-3 * * * *", "* * * foo *", "* * * * mon-xyz", "* * * * mon-", "*/ * * * *",
    "*-5 * * * *", "1.5 * * * *", "* * * dec-jan *", "* * jan * *", "mon * * * *", "* * * * 0-8",
    "* * * * 6-0", "5/0 * * * *", "* * * * fri-mon", "0-60 * * * *",
])
def test_invalid_expressions(expr):
    with pytest.raises(ValueError):
        next_run(expr, D(2024, 1, 1))


@pytest.mark.parametrize("expr", ["0 0 30 2 *", "0 0 31 4 *", "0 0 31 2,4,6,9,11 *"])
def test_never_matches(expr):
    with pytest.raises(ValueError):
        next_run(expr, D(2024, 1, 1))
    with pytest.raises(ValueError):
        next_runs(expr, D(2024, 1, 1), 1)


def test_validated_even_if_never_matches():
    with pytest.raises(ValueError):
        next_run("0 0 30 2 99", D(2024, 1, 1))


def test_after_types():
    with pytest.raises(ValueError):
        next_run("* * * * *", D(2024, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(TypeError):
        next_run("* * * * *", "2024-01-01")
    with pytest.raises(TypeError):
        next_run("* * * * *", date(2024, 1, 1))


def test_next_runs_basic():
    assert next_runs("*/30 * * * *", D(2024, 1, 1, 10, 0), 3) == [
        D(2024, 1, 1, 10, 30), D(2024, 1, 1, 11, 0), D(2024, 1, 1, 11, 30)]


def test_next_runs_calendar():
    assert next_runs("@daily", D(2024, 2, 27, 12, 0), 4) == [
        D(2024, 2, 28), D(2024, 2, 29), D(2024, 3, 1), D(2024, 3, 2)]


def test_next_runs_count_rules():
    assert next_runs("* * * * *", D(2024, 1, 1), 0) == []
    with pytest.raises(ValueError):
        next_runs("bad", D(2024, 1, 1), 0)
    with pytest.raises(ValueError):
        next_runs("* * * * *", D(2024, 1, 1), -1)


def test_next_runs_strictly_increasing():
    out = next_runs("*/7 * * * *", D(2024, 1, 1, 0, 0), 20)
    assert len(out) == 20
    assert all(b > a for a, b in zip(out, out[1:]))
    assert out[0] == D(2024, 1, 1, 0, 7)
