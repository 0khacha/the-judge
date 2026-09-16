from impl import run_job
def test_visible():
    try:
        run_job()
    except ValueError:
        pass
