import os, json
from _h import *
T = "D8_rooms"
r = mk(T, "reference")
p = lambda *a: os.path.join(r, *a)
rep(p("rooms/models.py"), "    capacity: int\n", "    capacity: int\n    buffer_minutes: int = 0\n")
S = p("rooms/service.py")
rep(S, "    def add_room(self, name, capacity):", "    def add_room(self, name, capacity, buffer_minutes=0):")
rep(S, "        if name in self.rooms:\n            raise ValueError(\"duplicate room %s\" % name)\n        self.rooms[name] = Room(name, capacity)",
       "        if name in self.rooms:\n            raise ValueError(\"duplicate room %s\" % name)\n        if not isinstance(buffer_minutes, int) or isinstance(buffer_minutes, bool) or not 0 <= buffer_minutes <= 60:\n            raise ValueError(\"buffer_minutes must be an integer from 0 to 60\")\n        self.rooms[name] = Room(name, capacity, buffer_minutes)")
rep(S, "    def _conflict(self, room, start, end, ignore=None):\n        for b in self._bookings.values():\n            if b.room == room and b.booking_id != ignore and calendar.overlaps(start, end, b.start, b.end):",
       "    def _conflict(self, room, start, end, ignore=None):\n        pad = timedelta(minutes=self.rooms[room].buffer_minutes)\n        for b in self._bookings.values():\n            if b.room == room and b.booking_id != ignore \\\n                    and calendar.overlaps(start, end + pad, b.start, b.end + pad):")
R = p("rooms/report.py")
rep(R, '        lines.append("%s (cap %d)" % (room.name, room.capacity))', '        if room.buffer_minutes:\n            lines.append("%s (cap %d, buffer %d min)" % (room.name, room.capacity, room.buffer_minutes))\n        else:\n            lines.append("%s (cap %d)" % (room.name, room.capacity))')

w = clone(T, "reference", "wrong_1")   # the buffer is only checked in book(); reschedule / free_slots / find_room ignore it
S1 = os.path.join(w, "rooms/service.py")
rep(S1, "        pad = timedelta(minutes=self.rooms[room].buffer_minutes)\n", "        pad = timedelta(0)\n")
rep(S1, "        self._check(room, start, end)\n        booking = Booking(", "        self._check(room, start, end)\n        pad = timedelta(minutes=r.buffer_minutes)\n        for b in self._bookings.values():\n            if b.room == room and calendar.overlaps(start, end + pad, b.start, b.end + pad):\n                raise Conflict(\"room %s needs a %d minute buffer\" % (room, r.buffer_minutes))\n        booking = Booking(")
w = clone(T, "reference", "wrong_2")   # a rescheduled booking is checked against itself
S2 = os.path.join(w, "rooms/service.py")
rep(S2, "            if b.room == room and b.booking_id != ignore \\\n                    and calendar", "            if b.room == room \\\n                    and calendar")
json.dump({"task": T, "lines": 0, "change_requirements": 7, "traps": [
 "buffer must apply in reschedule/free_slots/find_room, not only book",
 "gap also required before an existing booking (end + buffer > existing.start)",
 "buffer ignores opening hours (no RuleError for 18:00 end)",
 "reschedule must not conflict with itself, even through its own buffer",
 "free_slots equals exactly the set book would accept",
 "report header only with buffer; utilization excludes buffer",
 "regression: reschedule overlapping own old slot with buffer 0"]}, open(os.path.join(H, T, "label.json"), "w"), indent=1)
