from dataclasses import dataclass
from datetime import datetime


@dataclass
class Room:
    name: str
    capacity: int


@dataclass
class Booking:
    booking_id: int
    room: str
    start: datetime
    end: datetime
    who: str
    attendees: int = 1

    @property
    def minutes(self):
        return int((self.end - self.start).total_seconds() // 60)
