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
