class InvalidTransition(Exception):
    pass


_EVENTS = ("assign", "start", "block", "unblock", "complete", "close", "reopen", "cancel")
_ALLOWED = {
    "assign": ("NEW", "ASSIGNED", "REOPENED"),
    "start": ("ASSIGNED", "REOPENED"),
    "block": ("ASSIGNED", "IN_PROGRESS"),
    "unblock": ("BLOCKED",),
    "complete": ("IN_PROGRESS",),
    "close": ("DONE",),
    "reopen": ("DONE", "CLOSED"),
    "cancel": ("NEW", "ASSIGNED", "IN_PROGRESS", "BLOCKED", "DONE", "REOPENED"),
}
MAX_REOPENS = 2


def _blank(v):
    return not isinstance(v, str) or not v.strip()


class Workflow:
    def __init__(self):
        self._state = "NEW"
        self._assignee = None
        self._reason = None
        self._blocked_from = None
        self._reopens = 0
        self._history = []
        self._snapshots = []
        self._listeners = []

    @property
    def state(self):
        return self._state

    @property
    def assignee(self):
        return self._assignee

    @property
    def block_reason(self):
        return self._reason

    @property
    def reopen_count(self):
        return self._reopens

    @property
    def history(self):
        return list(self._history)

    def _allowed(self, event):
        if self._state not in _ALLOWED[event]:
            return False
        if event == "reopen" and self._reopens >= MAX_REOPENS:
            return False
        return True

    def allowed_events(self):
        return sorted(e for e in _EVENTS if self._allowed(e))

    def on_transition(self, callback):
        self._listeners.append(callback)

    def apply(self, event, **kwargs):
        if event not in _ALLOWED:
            raise ValueError("unknown event %r" % (event,))
        if event == "assign" and _blank(kwargs.get("user")):
            raise ValueError("user required")
        if not self._allowed(event):
            raise InvalidTransition("%s not allowed in %s" % (event, self._state))
        if event == "assign":
            user = kwargs.get("user")
            if self._state == "ASSIGNED" and user == self._assignee:
                raise InvalidTransition("already assigned to %r" % (user,))
            if _blank(user):
                raise ValueError("user required")
        if event == "block":
            reason = kwargs.get("reason")
            if _blank(reason):
                raise ValueError("reason required")
        snap = (self._state, self._assignee, self._reason, self._blocked_from, self._reopens)
        old = self._state
        if event == "assign":
            new = "ASSIGNED"
            self._assignee = kwargs["user"]
        elif event == "start":
            new = "IN_PROGRESS"
        elif event == "block":
            new = "BLOCKED"
            self._blocked_from = old
            self._reason = kwargs["reason"]
        elif event == "unblock":
            new = "IN_PROGRESS"
            self._blocked_from = None
            self._reason = None
        elif event == "complete":
            new = "DONE"
        elif event == "close":
            new = "CLOSED"
        elif event == "reopen":
            new = "REOPENED"
            self._reopens += 1
        else:
            new = "CANCELLED"
            self._reason = None
            self._blocked_from = None
        self._state = new
        self._snapshots.append(snap)
        self._history.append((old, event, new))
        for cb in list(self._listeners):
            cb(old, event, new)
        return new

    def undo(self):
        if not self._snapshots:
            raise InvalidTransition("nothing to undo")
        (self._state, self._assignee, self._reason,
         self._blocked_from, self._reopens) = self._snapshots.pop()
        self._history.pop()
        return self._state
