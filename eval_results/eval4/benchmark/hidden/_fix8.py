f="D8_rooms/test_hidden.py"; s=open(f).read()
def r(a,b):
    global s
    assert s.count(a)==1,a; s=s.replace(a,b)
r('at(9, 45) if False else at(10)','at(10)')
r('at(13, 45) if False else at(14)','at(14)')
r('    assert s.bookings() == [b2, b3, b1, b4] or s.bookings() == [b3, b2, b1, b4]\n','    assert s.bookings() == [b3, b2, b1, b4]\n')
r('''        s.reschedule(first.booking_id, at(9, 30), at(10, 15))
    assert (first.start, first.end) == (at(9), at(10))
    s.reschedule(first.booking_id, at(9, 15), at(10, 15))
    with pytest.raises(Conflict):
        s.reschedule(first.booking_id, at(9, 30), at(10, 30))''','''        s.reschedule(first.booking_id, at(9, 30), at(10, 30))
    assert (first.start, first.end) == (at(9), at(10))
    s.reschedule(first.booking_id, at(9, 15), at(10, 15))
    with pytest.raises(Conflict):
        s.reschedule(first.booking_id, at(9, 45), at(10, 30))''')
r('s.book("B", at(10, 30), at(11), "bob")\n    assert s.find_room(at(9), at(10), 2) is None','s.book("B", at(10), at(10, 30), "bob")\n    assert s.find_room(at(9), at(10), 2) is None')
open(f,"w").write(s)
