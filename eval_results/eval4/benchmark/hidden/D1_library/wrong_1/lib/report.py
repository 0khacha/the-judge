"""Plain-text reports."""
from . import fines, policy


def member_summary(lib, member_id):
    member = lib._member(member_id)
    loans = lib.active_loans(member_id)
    lines = [
        "Member #%d: %s" % (member.member_id, member.name),
        "Tier: %s" % member.tier,
        "Active loans: %d/%d" % (len(loans), policy.max_loans(member)),
        "Fines owed: %.2f" % lib.fines_owed[member_id],
    ]
    for loan in loans:
        lines.append("  - %s due %s" % (lib.books[loan.isbn].title, loan.due.isoformat()))
    return "\n".join(lines)


def overdue_report(lib):
    """One line per overdue loan, most late first: title | member | N days late | fine X.XX"""
    today = lib.today()
    rows = []
    for loan in lib.overdue():
        late = fines.days_late(loan, today)
        fine = fines.fine_for(loan, lib.books[loan.isbn].price, today)
        rows.append((late, "%s | %s | %d days late | fine %.2f" % (
            lib.books[loan.isbn].title, lib.members[loan.member_id].name, late, fine)))
    rows.sort(key=lambda r: -r[0])
    if not rows:
        return "No overdue loans."
    return "\n".join(r[1] for r in rows)
