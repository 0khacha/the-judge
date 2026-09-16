fixed_code = '''def validate_luhn(card_number: str) -> bool:
    digits = [int(c) for c in card_number if c.isdigit()]
    if not digits:
        return False

    checksum = 0
    reverse_digits = digits[::-1]

    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            if doubled > 9:
                doubled -= 9
            checksum += doubled
        else:
            checksum += digit

    return checksum % 10 == 0
'''
with open("luhn.py", "w", encoding="utf-8") as f:
    f.write(fixed_code)
