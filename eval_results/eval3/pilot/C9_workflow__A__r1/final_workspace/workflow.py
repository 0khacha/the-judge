"""Ticket workflow state machine."""

STATES = (
    "NEW",
    "ASSIGNED",
    "IN_PROGRESS",
    "BLOCKED",
    "DONE",
    "CLOSED",
    "REOPENED",
    "CANCELLED",
)

EVENTS = (
    "assign",
    "start",
    "block",
    "unblock",
    "complete",
    "close",
    "reopen",
    "cancel",
)

MAX_REOPENS = 2

# Allowed source states per event (state-based rule only).
_FROM_STATES = {
    "assign": {"NEW", "ASSIGNED", "REOPENED"},
    "start": {"ASSIGNED", "REOPENED"},
    "block": {"ASSIGNED", "IN_PROGRESS"},
    "unblock": {"BLOCKED"},
    "complete": {"IN_PROGRESS"},
    "close": {"DONE"},
    "reopen": {"DONE", "CLOSED"},
    "cancel": set(STATES) - {"CLOSED", "CANCELLED"},
}

_TARGET_STATES = {
    "assign": "ASSIGNED",
    "start": "IN_PROGRESS",
    "block": "BLOCKED",
    "complete": "DONE",
    "close": "CLOSED",
    "reopen": "REOPENED",
    "cancel": "CANCELLED",
}


class InvalidTransition(Exception):
    """Raised when an event is not allowed in the current state or rule."""


def _is_non_blank(value):
    return isinstance(value, str) and value.strip() != ""


class Workflow:
    def __init__(self):
        self._state = "NEW"
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
        return self._block_reason if self._state == "BLOCKED" else None

    @property
    def reopen_count(self):
        return self._reopen_count

    @property
    def history(self):
        return list(self._history)

    def allowed_events(self):
        result = []
        for event in EVENTS:
            if self._state not in _FROM_STATES[event]:
                continue
            if event == "reopen" and self._reopen_count >= MAX_REOPENS:
                continue
            result.append(event)
        return sorted(result)

    def on_transition(self, callback):
        self._listeners.append(callback)

    # ----- transitions ---------------------------------------------------
    def apply(self, event, **kwargs):
        # 1. unknown event
        if not isinstance(event, str) or event not in EVENTS:
            raise ValueError(f"unknown event: {event!r}")

        # 2. state / rule violations
        if self._state not in _FROM_STATES[event]:
            raise InvalidTransition(f"{event} not allowed in state {self._state}")
        if event == "reopen" and self._reopen_count >= MAX_REOPENS:
            raise InvalidTransition("reopen limit reached")
        if event == "assign" and self._state == "ASSIGNED":
            user = kwargs.get("user")
            if _is_non_blank(user) and user == self._assignee:
                raise InvalidTransition("user is already the assignee")

        # 3. required kwargs
        new_user = None
        new_reason = None
        if event == "assign":
            user = kwargs.get("user")
            if not _is_non_blank(user):
                raise ValueError("assign requires a non-blank user")
            new_user = user
        elif event == "block":
            reason = kwargs.get("reason")
            if not _is_non_blank(reason):
                raise ValueError("block requires a non-blank reason")
            new_reason = reason
        elif event == "cancel":
            new_reason = kwargs.get("reason")

        # Validation passed: snapshot, then mutate.
        from_state = self._state
        self._undo_stack.append(
            (
                self._state,
                self._assignee,
                self._block_reason,
                self._blocked_from,
                self._reopen_count,
            )
        )

        if event == "unblock":
            to_state = self._blocked_from
            self._block_reason = None
            self._blocked_from = None
        else:
            to_state = _TARGET_STATES[event]
            if event == "assign":
                self._assignee = new_user
            elif event == "block":
                self._blocked_from = from_state
                self._block_reason = new_reason
            elif event == "cancel":
                self._block_reason = None
                self._blocked_from = None
            elif event == "reopen":
                self._reopen_count += 1

        self._state = to_state
        self._history.append((from_state, event, to_state))

        for callback in list(self._listeners):
            callback(from_state, event, to_state)

        return self._state

    def undo(self):
        if not self._undo_stack:
            raise InvalidTransition("nothing to undo")
        (
            self._state,
            self._assignee,
            self._block_reason,
            self._blocked_from,
            self._reopen_count,
        ) = self._undo_stack.pop()
        self._history.pop()
        return self._state
