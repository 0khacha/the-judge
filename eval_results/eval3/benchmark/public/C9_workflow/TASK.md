# C9: ticket workflow state machine

Write `workflow.py` (project root, standard library only) with `class InvalidTransition(Exception)` and `class Workflow`.

## States and events
States are the strings `NEW`, `ASSIGNED`, `IN_PROGRESS`, `BLOCKED`, `DONE`, `CLOSED`, `REOPENED`, `CANCELLED`. A new `Workflow()` is in `NEW`. Events are the strings `assign`, `start`, `block`, `unblock`, `complete`, `close`, `reopen`, `cancel`.

`apply(event, **kwargs) -> str` performs one event and returns the new state.

| event | allowed from | to | notes |
|---|---|---|---|
| `assign` | NEW, ASSIGNED, REOPENED | ASSIGNED | kwarg `user` (non-blank str) required; sets the assignee. In ASSIGNED the new user must differ from the current assignee, otherwise `InvalidTransition`. |
| `start` | ASSIGNED, REOPENED | IN_PROGRESS | |
| `block` | ASSIGNED, IN_PROGRESS | BLOCKED | kwarg `reason` (non-blank str) required; remembers the state it was blocked from. |
| `unblock` | BLOCKED | the state the ticket was blocked from | clears the block reason. |
| `complete` | IN_PROGRESS | DONE | |
| `close` | DONE | CLOSED | |
| `reopen` | DONE, CLOSED | REOPENED | at most 2 reopens in the ticket's life; a third attempt is `InvalidTransition`. |
| `cancel` | every state except CLOSED and CANCELLED | CANCELLED | optional kwarg `reason`. |

## Errors, in this order of precedence
1. An unknown event name raises `ValueError`.
2. An event that is not allowed in the current state (or violates the same-assignee or reopen-limit rule) raises `InvalidTransition`.
3. Missing or blank required kwargs (`user`, `reason`) raise `ValueError`.
Unexpected extra kwargs are ignored. Any failed `apply` leaves state, assignee, history and counters exactly as they were and calls no listeners. Example: `apply("assign")` (no user) in state DONE raises `InvalidTransition`, not `ValueError`.

## Observers and queries
* `state` (property), `assignee` (property, `None` until the first assign; it is kept after later transitions including cancel), `block_reason` (property: the reason while BLOCKED, otherwise `None`), `reopen_count` (property).
* `history` (property): a new list of `(from_state, event, to_state)` tuples, one per successful transition, oldest first.
* `allowed_events() -> list[str]`: sorted names of the events that are allowed in the current state, ignoring kwargs and the same-assignee rule (so `assign` is listed in ASSIGNED); `reopen` is not listed once `reopen_count` is 2.
* `on_transition(callback)`: registers `callback(from_state, event, to_state)`, called after each successful `apply` (state and history already updated) in registration order. If a callback raises, the exception propagates to the caller of `apply` and the transition stays applied; later callbacks are not called.

## Undo
`undo()` reverts the most recent successful transition completely (state, assignee, block reason and blocked-from state, reopen count) and removes its history entry; it returns the restored state. It can be called repeatedly back to the start. With nothing to undo it raises `InvalidTransition`. Undo does not call listeners and is not itself recorded in the history.
