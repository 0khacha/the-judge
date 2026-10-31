"""Command line front end: main(argv, lib, out=print) -> exit code."""
from .errors import LibraryError
from . import report

USAGE = "commands: add-book, add-member, checkout, return, renew, summary, overdue"


def _add_book(lib, args, out):
    if len(args) < 3:
        raise LibraryError("usage: add-book ISBN TITLE PRICE [COPIES]")
    copies = int(args[3]) if len(args) > 3 else 1
    book = lib.add_book(args[0], args[1], float(args[2]), copies)
    out("book %s (%d copies)" % (book.isbn, book.copies))


def _add_member(lib, args, out):
    tier = "standard"
    if len(args) == 3 and args[1] == "--tier":
        tier = args[2]
    elif len(args) != 1:
        raise LibraryError("usage: add-member NAME [--tier TIER]")
    member = lib.add_member(args[0], tier)
    out("member %d %s" % (member.member_id, member.name))


def _set_tier(lib, args, out):
    if len(args) != 2:
        raise LibraryError("usage: set-tier ID TIER")
    member = lib.set_tier(int(args[0]), args[1])
    out("member %d tier %s" % (member.member_id, member.tier))


def _checkout(lib, args, out):
    loan = lib.checkout(args[0], int(args[1]))
    out("loan %d due %s" % (loan.loan_id, loan.due.isoformat()))


def _return(lib, args, out):
    fine = lib.return_book(int(args[0]))
    out("returned, fine %.2f" % fine)


def _renew(lib, args, out):
    loan = lib.renew(int(args[0]))
    out("loan %d due %s" % (loan.loan_id, loan.due.isoformat()))


def _summary(lib, args, out):
    out(report.member_summary(lib, int(args[0])))


def _overdue(lib, args, out):
    out(report.overdue_report(lib))


COMMANDS = {
    "add-book": _add_book, "add-member": _add_member, "checkout": _checkout,
    "set-tier": _set_tier, "return": _return, "renew": _renew, "summary": _summary, "overdue": _overdue,
}


def main(argv, lib, out=print):
    if not argv or argv[0] not in COMMANDS:
        out(USAGE)
        return 2
    try:
        COMMANDS[argv[0]](lib, argv[1:], out)
    except (LibraryError, KeyError, ValueError, IndexError) as exc:
        out("error: %s" % (exc.args[0] if exc.args else exc))
        return 1
    return 0
