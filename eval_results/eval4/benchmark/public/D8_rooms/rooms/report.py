"""Text reports."""
from . import rules


def day_schedule(sched, day):
    lines = ["Schedule for %s" % day.isoformat()]
    for name in sorted(sched.rooms):
        room = sched.rooms[name]
        lines.append("%s (cap %d)" % (room.name, room.capacity))
        found = sched.bookings(room=name, day=day)
        for b in found:
            lines.append("  %s-%s %s (%d)" % (b.start.strftime("%H:%M"), b.end.strftime("%H:%M"), b.who, b.attendees))
        if not found:
            lines.append("  (no bookings)")
    return "\n".join(lines)


def utilization(sched, day):
    """{room: booked minutes / opening minutes} for the day."""
    result = {}
    for name in sorted(sched.rooms):
        booked = sum(b.minutes for b in sched.bookings(room=name, day=day))
        result[name] = booked / rules.OPEN_MINUTES
    return result
