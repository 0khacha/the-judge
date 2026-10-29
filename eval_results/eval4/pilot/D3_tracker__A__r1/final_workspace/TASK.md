# Ticket: recurring tasks

People keep re-entering the same weekly chores. Please add recurring tasks.

1. `TaskStore.add(title, due=None, priority=2, tags=(), deps=(), repeat=None)`. `repeat` is `None`, `"daily"`, `"weekly"` or `"monthly"`; anything else raises `ValueError`. A recurring task must have a due date, otherwise `ValueError`. A rejected `add` creates nothing and uses no id. `Task` gets two new attributes: `repeat` (default `None`) and `next_id` (default `None`).
2. Completing a recurring task (via `complete`) marks it done as before and creates the next occurrence: a new open task with the same title, priority, a copy of the tags, the same `repeat`, no dependencies, and a fresh id (the normal id counter). `complete` still returns the task that was completed, and its `next_id` is set to the id of the new task. Completing a task that is not recurring does not create anything. A completion that fails (already done, `BlockedError`) creates nothing.
3. The due date of the new task is computed from the *old due date*, not from the completion date (even if that gives a date in the past): daily = +1 day, weekly = +7 days, monthly = same day of the month in the next month, clamped to the last day of that month (31 Jan 2024 -> 29 Feb 2024, 31 Mar -> 30 Apr, December rolls into January of the next year).
4. `reopen` of a task whose successor (`next_id`) is still open raises `ValueError` and changes nothing. Otherwise the task is reopened as before and its `next_id` is reset to `None`.
5. `delete` of a task that some other task has as `next_id` sets that task's `next_id` back to `None`.
6. `storage.dump` writes `"repeat"` and `"next_id"` for every task (null when not set); `storage.load` must still accept data without these keys (older files).
7. `views.agenda`: the line of a recurring task gets the text ` (repeats <kind>)` after the `(due ...)` part and before the ` OVERDUE` flag, for example `  #3 [P2] Water plants (due 2024-01-12) (repeats weekly) OVERDUE`.
8. Command line: `add` takes `--repeat KIND` (a missing due date or bad kind gives `error: ...` and exit code 1); `done` prints `done #<id>` and, when a new occurrence was created, a second line `next #<newid> due <date>`; the `list` and `ready` lines of recurring tasks end with ` repeat <kind>`.

Everything else must keep working as it does now.
