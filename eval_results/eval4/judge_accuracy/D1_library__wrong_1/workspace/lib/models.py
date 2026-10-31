from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Book:
    isbn: str
    title: str
    price: float
    copies: int = 1


@dataclass
class Member:
    member_id: int
    name: str
    tier: str = "standard"


@dataclass
class Loan:
    loan_id: int
    isbn: str
    member_id: int
    out: date
    due: date
    returned: Optional[date] = None
    renewals: int = 0

    @property
    def active(self):
        return self.returned is None
