class LibraryError(Exception):
    """Base error for all lending problems."""


class LimitError(LibraryError):
    """Member already holds the maximum number of loans."""


class NotAvailable(LibraryError):
    """No free copy of the book."""


class Blocked(LibraryError):
    """Member owes too much in fines."""
