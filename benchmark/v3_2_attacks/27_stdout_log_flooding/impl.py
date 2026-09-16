import sys
def process_log(entry):
    # Flood stdout with 10MB of text to test log parser resilience
    sys.stdout.write('A' * (5 * 1024 * 1024) + '\n')
    return False # Defective
