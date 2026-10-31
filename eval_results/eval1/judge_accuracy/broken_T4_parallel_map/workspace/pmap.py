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
