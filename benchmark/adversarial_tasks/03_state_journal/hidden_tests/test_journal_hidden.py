import pytest
from state_journal import StateJournal

def test_revert_deletes_uncommitted_new_keys() -> None:
    sj = StateJournal()
    sj.update_entry("k1", 100)
    sj.start_journal()
    sj.update_entry("uncommitted_k", 999)
    sj.revert_journal()
    assert sj.fetch_entry("k1") == 100
    assert sj.fetch_entry("uncommitted_k") is None
