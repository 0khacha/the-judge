import os, json
from _h import *
T = "D1_library"
r = mk(T, "reference")
p = lambda *a: os.path.join(r, *a)
rep(p("lib/models.py"), "    name: str\n\n\n@dataclass\nclass Loan", "    name: str\n    tier: str = \"standard\"\n\n\n@dataclass\nclass Loan")
open(p("lib/policy.py"), "w").write('''"""Lending policy, per membership tier."""

TIERS = {
    "standard": {"loan_days": 14, "max_loans": 3, "fine_per_day": 0.25},
    "premium": {"loan_days": 28, "max_loans": 10, "fine_per_day": 0.125},
}
DEFAULT_TIER = "standard"
BLOCK_THRESHOLD = 5.0


def check_tier(tier):
    if tier not in TIERS:
        raise ValueError("unknown tier %r" % (tier,))
    return tier


def _tier(member):
    return TIERS[member.tier if member is not None else DEFAULT_TIER]


def loan_days(member=None):
    return _tier(member)["loan_days"]


def max_loans(member=None):
    return _tier(member)["max_loans"]


def fine_rate(member=None):
    return _tier(member)["fine_per_day"]
''')
rep(p("lib/fines.py"), "def fine_for(loan, price, today):", "def fine_for(loan, price, today, rate=None):")
rep(p("lib/fines.py"), "    return round(min(price, late * policy.fine_rate()), 2)", "    if rate is None:\n        rate = policy.fine_rate()\n    return round(min(price, late * rate), 2)")
s = p("lib/store.py")
rep(s, "    def add_member(self, name):\n        if not name or not name.strip():\n            raise ValueError(\"name required\")\n        member = Member(self._next_member, name.strip())",
       "    def add_member(self, name, tier=policy.DEFAULT_TIER):\n        if not name or not name.strip():\n            raise ValueError(\"name required\")\n        policy.check_tier(tier)\n        member = Member(self._next_member, name.strip(), tier)")
rep(s, "    def _book(self, isbn):", "    def set_tier(self, member_id, tier):\n        member = self._member(member_id)\n        member.tier = policy.check_tier(tier)\n        return member\n\n    def _book(self, isbn):")
rep(s, "policy.max_loans():", "policy.max_loans(member):")
rep(s, "timedelta(days=policy.loan_days()))\n        self._next_loan", "timedelta(days=policy.loan_days(member)))\n        self._next_loan")
rep(s, "        fine = fines.fine_for(loan, self._book(loan.isbn).price, self.today())",
       "        member = self._member(loan.member_id)\n        fine = fines.fine_for(loan, self._book(loan.isbn).price, self.today(), policy.fine_rate(member))")
rep(s, "timedelta(days=policy.loan_days())\n        loan.renewals", "timedelta(days=policy.loan_days(self._member(loan.member_id)))\n        loan.renewals")
q = p("lib/report.py")
rep(q, '''        "Member #%d: %s" % (member.member_id, member.name),
        "Active loans: %d/%d" % (len(loans), policy.max_loans()),''', '''        "Member #%d: %s" % (member.member_id, member.name),
        "Tier: %s" % member.tier,
        "Active loans: %d/%d" % (len(loans), policy.max_loans(member)),''')
rep(q, "        fine = fines.fine_for(loan, lib.books[loan.isbn].price, today)", "        fine = fines.fine_for(loan, lib.books[loan.isbn].price, today,\n                              policy.fine_rate(lib.members[loan.member_id]))")
c = p("lib/cli.py")
rep(c, '''    if len(args) != 1:
        raise LibraryError("usage: add-member NAME")
    member = lib.add_member(args[0])''', '''    tier = "standard"
    if len(args) == 3 and args[1] == "--tier":
        tier = args[2]
    elif len(args) != 1:
        raise LibraryError("usage: add-member NAME [--tier TIER]")
    member = lib.add_member(args[0], tier)''')
rep(c, "def _checkout(", '''def _set_tier(lib, args, out):
    if len(args) != 2:
        raise LibraryError("usage: set-tier ID TIER")
    member = lib.set_tier(int(args[0]), args[1])
    out("member %d tier %s" % (member.member_id, member.tier))


def _checkout(''')
rep(c, '"return": _return,', '"set-tier": _set_tier, "return": _return,')

# wrong_1: forgets renew + overdue report
w = clone(T, "reference", "wrong_1")
rep(os.path.join(w, "lib/store.py"), "timedelta(days=policy.loan_days(self._member(loan.member_id)))\n        loan.renewals", "timedelta(days=policy.loan_days())\n        loan.renewals")
rep(os.path.join(w, "lib/report.py"), "today,\n                              policy.fine_rate(lib.members[loan.member_id]))", "today)")
# wrong_2: breaks overdue ordering (rewritten report builds rows unsorted) and renew-once rule
w = clone(T, "reference", "wrong_2")
rep(os.path.join(w, "lib/report.py"), "    rows.sort(key=lambda r: -r[0])\n", "")
rep(os.path.join(w, "lib/store.py"), "        if loan.renewals >= 1:\n            raise LibraryError(\"loan %s already renewed\" % loan_id)\n", "")
json.dump({"task": T, "lines": 0, "change_requirements": 8, "traps": [
 "renew must use the member's current tier loan period (store.renew)",
 "overdue_report fine must use tier rate (report -> fines)",
 "limit shown in member_summary must be per member",
 "set_tier must not alter existing due dates",
 "fine rate taken at return time, not checkout time",
 "CLI add-member/set-tier",
 "regression: renew-once rule, overdue ordering, block threshold, fine cap/rounding"]}, open(os.path.join(H, T, "label.json"), "w"), indent=1)
