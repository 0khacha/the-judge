"""The scheduler."""
from datetime import datetime, timedelta

from . import calendar, rules
from .errors import CapacityError, Conflict, RuleError, SchedulerError
from .models import Booking, Room


class Scheduler:
    def __init__(self, clock=None):
        self.clock = clock or datetime.now
        self.rooms = {}
        self._bookings = {}
        self._next_id = 1

    # -- rooms -------------------------------------------------------
    def add_room(self, name, capacity, buffer_minutes=0):
        name = (name or "").strip()
        if not name:
            raise ValueError("room name required")
        if not isinstance(capacity, int) or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        if name in self.rooms:
            raise ValueError("duplicate room %s" % name)
        if not isinstance(buffer_minutes, int) or isinstance(buffer_minutes, bool) or not 0 <= buffer_minutes <= 60:
            raise ValueError("buffer_minutes must be an integer from 0 to 60")
        self.rooms[name] = Room(name, capacity, buffer_minutes)
        return self.rooms[name]

    def room(self, name):
        if name not in self.rooms:
            raise KeyError(name)
        return self.rooms[name]

    # -- internals ---------------------------------------------------
    def _conflict(self, room, start, end, ignore=None):
        pad = timedelta(0)
        for b in self._bookings.values():
            if b.room == room and b.booking_id != ignore \
                    and calendar.overlaps(start, end + pad, b.start, b.end + pad):
                return b
        return None

    def _check(self, room, start, end, ignore=None):
        rules.validate(start, end)
        if start < self.clock():
            raise RuleError("start is in the past")
        other = self._conflict(room, start, end, ignore)
        if other is not None:
            raise Conflict("room %s is taken by booking %d" % (room, other.booking_id))

    # -- bookings ----------------------------------------------------
    def book(self, room, start, end, who, attendees=1):
        r = self.room(room)
        if attendees < 1 or attendees > r.capacity:
            raise CapacityError("room %s holds %d, asked for %d" % (room, r.capacity, attendees))
        self._check(room, start, end)
        pad = timedelta(minutes=r.buffer_minutes)
        for b in self._bookings.values():
            if b.room == room and calendar.overlaps(start, end + pad, b.start, b.end + pad):
                raise Conflict("room %s needs a %d minute buffer" % (room, r.buffer_minutes))
        booking = Booking(self._next_id, room, start, end, who, attendees)
        self._next_id += 1
        self._bookings[booking.booking_id] = booking
        return booking

    def get(self, booking_id):
        if booking_id not in self._bookings:
            raise KeyError(booking_id)
        return self._bookings[booking_id]

    def cancel(self, booking_id):
        booking = self.get(booking_id)
        if booking.start <= self.clock():
            raise RuleError("booking %d has already started" % booking_id)
        del self._bookings[booking_id]
        return booking

    def reschedule(self, booking_id, start, end):
        booking = self.get(booking_id)
        self._check(booking.room, start, end, ignore=booking_id)
        booking.start, booking.end = start, end
        return booking

    def bookings(self, room=None, day=None):
        found = [b for b in self._bookings.values()
                 if (room is None or b.room == room) and (day is None or b.start.date() == day)]
        return sorted(found, key=lambda b: (b.start, b.booking_id))

    # -- searching ---------------------------------------------------
    def free_slots(self, room, day, minutes):
        """Quarter-hour start times on `day` at which a booking of `minutes` would be accepted."""
        self.room(room)
        slots = []
        start = datetime(day.year, day.month, day.day, rules.OPEN.hour, rules.OPEN.minute)
        last = datetime(day.year, day.month, day.day, rules.CLOSE.hour, rules.CLOSE.minute)
        while start < last:
            try:
                self._check(room, start, start + timedelta(minutes=minutes))
                slots.append(start)
            except SchedulerError:
                pass
            except ValueError:
                pass
            start += timedelta(minutes=rules.STEP)
        return slots

    def find_room(self, start, end, attendees):
        rules.validate(start, end)
        for name in sorted(self.rooms):
            if attendees > self.rooms[name].capacity:
                continue
            if self._conflict(name, start, end) is None:
                return name
        return None
