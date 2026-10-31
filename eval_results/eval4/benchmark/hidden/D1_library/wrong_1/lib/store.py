"""The Library: books, members and loans."""
from datetime import date, timedelta

from . import fines, policy
from .errors import Blocked, LibraryError, LimitError, NotAvailable
from .models import Book, Loan, Member


class Library:
    def __init__(self, clock=None):
        self.clock = clock or date.today
        self.books = {}
        self.members = {}
        self.loans = []
        self.fines_owed = {}
        self._next_member = 1
        self._next_loan = 1

    def today(self):
        return self.clock()

    # -- catalogue ---------------------------------------------------
    def add_book(self, isbn, title, price, copies=1):
        """Add a book; adding an existing isbn only adds copies."""
        if copies < 1:
            raise ValueError("copies must be >= 1")
        if isbn in self.books:
            self.books[isbn].copies += copies
            return self.books[isbn]
        book = Book(isbn, title, float(price), copies)
        self.books[isbn] = book
        return book

    def add_member(self, name, tier=policy.DEFAULT_TIER):
        if not name or not name.strip():
            raise ValueError("name required")
        policy.check_tier(tier)
        member = Member(self._next_member, name.strip(), tier)
        self._next_member += 1
        self.members[member.member_id] = member
        self.fines_owed[member.member_id] = 0.0
        return member

    def set_tier(self, member_id, tier):
        member = self._member(member_id)
        member.tier = policy.check_tier(tier)
        return member

    def _book(self, isbn):
        if isbn not in self.books:
            raise KeyError("unknown book %s" % isbn)
        return self.books[isbn]

    def _member(self, member_id):
        if member_id not in self.members:
            raise KeyError("unknown member %s" % member_id)
        return self.members[member_id]

    # -- queries -----------------------------------------------------
    def active_loans(self, member_id=None):
        return [l for l in self.loans if l.active and (member_id is None or l.member_id == member_id)]

    def available(self, isbn):
        book = self._book(isbn)
        out = len([l for l in self.active_loans() if l.isbn == isbn])
        return book.copies - out

    def overdue(self):
        today = self.today()
        return [l for l in self.active_loans() if l.due < today]

    # -- operations --------------------------------------------------
    def checkout(self, isbn, member_id):
        self._book(isbn)
        member = self._member(member_id)
        if self.fines_owed[member_id] >= policy.BLOCK_THRESHOLD:
            raise Blocked("member %s owes %.2f" % (member_id, self.fines_owed[member_id]))
        if len(self.active_loans(member_id)) >= policy.max_loans(member):
            raise LimitError("member %s has too many loans" % member_id)
        if self.available(isbn) < 1:
            raise NotAvailable(isbn)
        out = self.today()
        loan = Loan(self._next_loan, isbn, member_id, out, out + timedelta(days=policy.loan_days(member)))
        self._next_loan += 1
        self.loans.append(loan)
        return loan

    def _active_loan(self, loan_id):
        for loan in self.loans:
            if loan.loan_id == loan_id and loan.active:
                return loan
        raise LibraryError("no active loan %s" % loan_id)

    def return_book(self, loan_id):
        """Close a loan; returns the fine (also added to the member's fines_owed)."""
        loan = self._active_loan(loan_id)
        loan.returned = self.today()
        member = self._member(loan.member_id)
        fine = fines.fine_for(loan, self._book(loan.isbn).price, self.today(), policy.fine_rate(member))
        self.fines_owed[loan.member_id] = round(self.fines_owed[loan.member_id] + fine, 2)
        return fine

    def renew(self, loan_id):
        """Extend a loan by one loan period. Allowed once, and not when overdue."""
        loan = self._active_loan(loan_id)
        if loan.renewals >= 1:
            raise LibraryError("loan %s already renewed" % loan_id)
        if loan.due < self.today():
            raise LibraryError("loan %s is overdue" % loan_id)
        loan.due = loan.due + timedelta(days=policy.loan_days())
        loan.renewals += 1
        return loan

    def pay_fines(self, member_id, amount):
        self._member(member_id)
        if amount <= 0:
            raise ValueError("amount must be positive")
        self.fines_owed[member_id] = round(max(0.0, self.fines_owed[member_id] - amount), 2)
        return self.fines_owed[member_id]
