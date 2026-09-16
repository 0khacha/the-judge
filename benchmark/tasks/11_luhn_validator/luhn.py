def validate_luhn(card_number: str) -> bool:
    digits = [int(c) for c in card_number if c.isdigit()]
    if not digits:
        return False

    checksum = 0
    reverse_digits = digits[::-1]

    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            # FLAW: Condition doubled > 10 misses 10 (e.g. 5*2=10)
            if doubled > 10:
                doubled -= 9
            checksum += doubled
        else:
            checksum += digit

    return checksum % 10 == 0
