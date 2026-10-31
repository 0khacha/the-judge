import threading


def parallel_map(fn, items, workers: int = 4) -> list:
    if workers < 1:
        raise ValueError("workers must be >= 1")
    items = list(items)
    n = len(items)
    if n == 0:
        return []
    results = [None] * n
    errors = [None] * n
    lock = threading.Lock()
    state = {"next": 0}

    def worker():
        while True:
            with lock:
                i = state["next"]
                if i >= n:
                    return
                state["next"] = i + 1
            try:
                results[i] = fn(items[i])
            except BaseException as e:
                errors[i] = e

    threads = [threading.Thread(target=worker) for _ in range(min(workers, n))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    for e in errors:
        if e is not None:
            raise e
    return results
