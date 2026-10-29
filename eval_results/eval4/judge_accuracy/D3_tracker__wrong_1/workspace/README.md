# tracker - a small task tracker

* `tracker.models.Task` - id, title, due date, priority (1 low .. 3 high, default 2), tags, dependencies, status (`open` / `done`), `done_on`.
* `tracker.store.TaskStore(clock=date.today)` - `add`, `get`, `complete`, `reopen`, `delete`, `tasks`, `ready`, `overdue`.
  A task can only be completed when all its dependencies are done (`BlockedError`). A task that other open tasks depend on cannot be deleted.
* `tracker.storage` - `dump(store) -> dict` and `load(data, clock=None) -> TaskStore` (JSON-compatible).
* `tracker.views` - text `agenda` and `summary`.
* `tracker.cli` - `main(argv, store, out=print)`: `add`, `done`, `reopen`, `rm`, `list`, `ready`, `agenda`, `summary`.
