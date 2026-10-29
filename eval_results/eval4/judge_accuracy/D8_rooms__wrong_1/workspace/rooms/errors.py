class SchedulerError(Exception):
    """Base class."""


class Conflict(SchedulerError):
    """The room is not free."""


class CapacityError(SchedulerError):
    """Wrong number of attendees for the room."""


class RuleError(SchedulerError, ValueError):
    """The requested time violates a booking rule."""
