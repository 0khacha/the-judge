# rooms - meeting room booking

Naive `datetime`s, minutes granularity.

* `rooms.rules` - bookings must be on one day, start and end on a quarter hour, lie within opening hours (08:00-18:00), last at most 4 hours, and have `end > start`. Violations raise `RuleError`.
* `rooms.calendar.overlaps(a_start, a_end, b_start, b_end)` - half-open intervals: back-to-back bookings do not overlap.
* `rooms.service.Scheduler(clock=datetime.now)`
  * `add_room(name, capacity)`, `room(name)`
  * `book(room, start, end, who, attendees=1)` -> `Booking`. Errors: `RuleError` (rules, or start in the past), `CapacityError` (attendees < 1 or > capacity), `Conflict` (overlaps another booking of the room).
  * `cancel(booking_id)` (not for bookings that already started), `reschedule(booking_id, start, end)` (same checks as `book`; the booking never conflicts with itself),
  * `bookings(room=None, day=None)` sorted by start, `free_slots(room, day, minutes)` - the quarter-hour start times on `day` at which a booking of that many minutes would currently be accepted, `find_room(start, end, attendees)` - name of the first room (alphabetical) that has the capacity and is free, or `None`.
* `rooms.report` - `day_schedule(scheduler, day)` text and `utilization(scheduler, day)` (booked minutes / 600 opening minutes per room).
