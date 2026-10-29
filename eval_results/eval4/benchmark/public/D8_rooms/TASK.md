# Ticket: cleaning buffer between bookings

Facilities needs time to reset a room (chairs, whiteboard, ...) between meetings. Add a per-room buffer.

1. `Scheduler.add_room(name, capacity, buffer_minutes=0)`. `buffer_minutes` is an `int` from 0 to 60 (inclusive; no `bool`), otherwise `ValueError` and no room is created. `Room` gets the attribute `buffer_minutes`.
2. In a room with a buffer, every booking blocks the room for `buffer_minutes` after its end. Two bookings of the same room must be separated by a gap of at least the buffer: a new booking conflicts (`Conflict`) with an existing one if it starts earlier than `existing.end + buffer`, and also if it ends later than `existing.start - buffer`. A gap exactly equal to the buffer is fine. With buffer 0 nothing changes (back-to-back bookings are allowed). The buffer is a property of the room: other rooms are unaffected.
3. A buffer is not subject to the opening hours: a booking that ends at 18:00 is fine even though its buffer lies after closing. Buffers never carry over into another day.
4. The rule of point 2 is used everywhere conflicts matter: `book`, `reschedule`, `free_slots` and `find_room`. A rescheduled booking never conflicts with itself (including its own buffer); other bookings still count, with their buffer.
5. `free_slots(room, day, minutes)` still returns exactly the start times at which `book(room, start, start + minutes, ...)` would currently be accepted (ignoring capacity).
6. `report.day_schedule`: the header line of a room with a buffer becomes `<name> (cap <n>, buffer <m> min)`; rooms without a buffer keep `<name> (cap <n>)`.
7. `report.utilization` keeps counting only the booked minutes (the buffer is not counted as booked).

Everything else (booking rules, capacity checks, cancel, ordering, errors) must keep working as before.
