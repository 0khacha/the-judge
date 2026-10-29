from datetime import datetime

from cron import next_run, next_runs


def test_every_15():
    assert next_run("*/15 * * * *", datetime(2024, 1, 1, 10, 7)) == datetime(2024, 1, 1, 10, 15)


def test_weekday_morning():
    # 2024-03-01 is a Friday
    assert next_run("0 9 * * 1-5", datetime(2024, 3, 1, 10, 0)) == datetime(2024, 3, 4, 9, 0)


def test_next_runs():
    out = next_runs("@hourly", datetime(2024, 1, 1, 0, 0), 2)
    assert out == [datetime(2024, 1, 1, 1, 0), datetime(2024, 1, 1, 2, 0)]
