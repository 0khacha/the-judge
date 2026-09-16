def aggregate_csv(csv_text: str) -> dict:
    lines = csv_text.strip().splitlines()
    total = 0.0
    count = 0
    # BUG: Fails to check for non-numeric lines or empty lines, crashing with ValueError
    for line in lines:
        val = float(line.strip())
        total += val
        count += 1
    return {"sum": total, "avg": total / count if count else 0.0}
