from typing import Any, Dict, Optional

class StateJournal:
    """Journaled state rollback engine."""

    def __init__(self):
        self.state: Dict[str, Any] = {}
        self._journal_backup: Optional[Dict[str, Any]] = None

    def update_entry(self, key: str, val: Any) -> None:
        self.state[key] = val

    def fetch_entry(self, key: str) -> Optional[Any]:
        return self.state.get(key)

    def start_journal(self) -> None:
        self._journal_backup = dict(self.state)

    def revert_journal(self) -> None:
        if self._journal_backup is not None:
            # FLAW: Restores existing keys but fails to remove new keys added during journal!
            for k, v in self._journal_backup.items():
                self.state[k] = v
            self._journal_backup = None
