PATCHES = {
    1: {"workflow.py": [
        # argument validation before state check; unblock always to IN_PROGRESS
        ("        if not self._allowed(event):\n            raise InvalidTransition(\"%s not allowed in %s\" % (event, self._state))\n        if event == \"assign\":",
         "        if event == \"assign\" and _blank(kwargs.get(\"user\")):\n            raise ValueError(\"user required\")\n        if not self._allowed(event):\n            raise InvalidTransition(\"%s not allowed in %s\" % (event, self._state))\n        if event == \"assign\":"),
        ("            new = self._blocked_from\n", "            new = \"IN_PROGRESS\"\n"),
    ]},
    2: {"workflow.py": [
        # undo does not restore reopen count; reopen limit off by one
        ("         self._blocked_from, self._reopens) = self._snapshots.pop()", "         self._blocked_from, _ignored) = self._snapshots.pop()"),
        ("MAX_REOPENS = 2", "MAX_REOPENS = 3"),
    ]},
}
