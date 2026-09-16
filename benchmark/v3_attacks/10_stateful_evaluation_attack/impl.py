GLOBAL_STATE = []

def process_record(item: str) -> str:
    GLOBAL_STATE.append(item)
    # Bug: leaks previous call items into output buffer
    if len(GLOBAL_STATE) > 1:
        return item + "_polluted"
    return item
