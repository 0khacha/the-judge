from concurrent.futures import ThreadPoolExecutor


def parallel_map(fn, items, workers: int = 4) -> list:
    if workers < 1:
        raise ValueError("workers must be >= 1")
    items = list(items)
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(fn, x) for x in items]
    # executor exit waits for all futures; raise earliest-in-order exception
    results = []
    for f in futures:
        exc = f.exception()
        if exc is not None:
            raise exc
        results.append(f.result())
    return results
