from concurrent.futures import ThreadPoolExecutor


def parallel_map(fn, items, workers: int = 4) -> list:
    if workers < 1:
        raise ValueError("workers must be >= 1")
    items = list(items)
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(fn, item) for item in items]
    # executor exit waits for all futures; pick earliest failure by input order
    results = []
    for f in futures:
        exc = f.exception()
        if exc is not None:
            raise exc
        results.append(f.result())
    return results
