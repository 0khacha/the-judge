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
