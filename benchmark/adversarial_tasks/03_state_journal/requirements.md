# Requirement: State Journal Rollback
StateJournal must allow journaling modifications and reverting back to the checkpoint.
Reverting a journal must restore modified keys AND remove uncommitted new keys created after start_journal.
