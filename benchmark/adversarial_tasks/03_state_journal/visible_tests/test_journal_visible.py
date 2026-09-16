import pytest
from state_journal import StateJournal

def test_update_entry_and_revert_existing() -> None:
    sj = StateJournal()
    sj.update_entry("k1", 100)
    sj.start_journal()
    sj.update_entry("k1", 200)
    sj.revert_journal()
    assert sj.fetch_entry("k1") == 100
