"""Ticket workflow state machine (standard library only)."""

NEW = "NEW"
ASSIGNED = "ASSIGNED"
IN_PROGRESS = "IN_PROGRESS"
BLOCKED = "BLOCKED"
DONE = "DONE"
CLOSED = "CLOSED"
REOPENED = "REOPENED"
CANCELLED = "CANCELLED"

STATES = (NEW, ASSIGNED, IN_PROGRESS, BLOCKED, DONE, CLOSED, REOPENED, CANCELLED)

# Event -> set of states it may be applied from (unblock is special-cased).
_SOURCES = {
    "assign": {NEW, ASSIGNED, REOPENED},
    "start": {ASSIGNED, REOPENED},
    "block": {ASSIGNED, IN_PROGRESS},
    "unblock": {BLOCKED},
    "complete": {IN_PROGRESS},
    "close": {DONE},
    "reopen": {DONE, CLOSED},
    "cancel": set(STATES) - {CLOSED, CANCELLED},
}

# Event -> target state (unblock is resolved from the blocked-from state).
_TARGETS = {
    "assign": ASSIGNED,
    "start": IN_PROGRESS,
    "block": BLOCKED,
    "complete": DONE,
    "close": CLOSED,
    "reopen": REOPENED,
    "cancel": CANCELLED,
}

# Events that require a non-blank string keyword argument.
_REQUIRED_KWARG = {"assign": "user", "block": "reason"}

MAX_REOPENS = 2


class InvalidTransition(Exception):
    """An event is not allowed in the current state, or violates a rule."""


class Workflow:
    def __init__(self):
        self._state = NEW
        self._assignee = None
        self._block_reason = None
        self._blocked_from = None
        self._reopen_count = 0
        self._history = []
        self._listeners = []
        self._undo_stack = []

    # ----- queries -------------------------------------------------------

    @property
    def state(self):
        return self._state

    @property
    def assignee(self):
        return self._assignee

    @property
    def block_reason(self):
        return self._block_reason if self._state == BLOCKED else None

    @property
    def reopen_count(self):
        return self._reopen_count

    @property
    def history(self):
        return list(self._history)

    def _is_allowed(self, event):
        if self._state not in _SOURCES[event]:
            return False
        if event == "reopen" and self._reopen_count >= MAX_REOPENS:
            return False
        return True

    def allowed_events(self):
        return sorted(event for event in _SOURCES if self._is_allowed(event))

    # ----- observers -----------------------------------------------------

    def on_transition(self, callback):
        self._listeners.append(callback)

    # ----- transitions ---------------------------------------------------

    def apply(self, event, **kwargs):
        if not isinstance(event, str) or event not in _SOURCES:
            raise ValueError(f"unknown event: {event!r}")

        if not self._is_allowed(event):
            raise InvalidTransition(f"{event!r} is not allowed in state {self._state}")

        if event == "assign" and self._state == ASSIGNED:
            if kwargs.get("user") == self._assignee:
                raise InvalidTransition("ticket is already assigned to this user")

        required = _REQUIRED_KWARG.get(event)
        if required is not None:
            value = kwargs.get(required)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{event!r} requires a non-blank {required!r}")

        from_state = self._state
        if event == "unblock":
            to_state = self._blocked_from
        else:
            to_state = _TARGETS[event]

        self._undo_stack.append(
            (self._state, self._assignee, self._block_reason,
             self._blocked_from, self._reopen_count)
        )

        if event == "assign":
            self._assignee = kwargs["user"]
        elif event == "block":
            self._blocked_from = from_state
            self._block_reason = kwargs["reason"]
        elif event in ("unblock", "cancel"):
            self._block_reason = None
            self._blocked_from = None
        elif event == "reopen":
            self._reopen_count += 1

        self._state = to_state
        self._history.append((from_state, event, to_state))

        for callback in list(self._listeners):
            callback(from_state, event, to_state)

        return to_state

    def undo(self):
        if not self._undo_stack:
            raise InvalidTransition("nothing to undo")
        (self._state, self._assignee, self._block_reason,
         self._blocked_from, self._reopen_count) = self._undo_stack.pop()
        self._history.pop()
        return self._state
