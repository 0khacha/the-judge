import sys
# Deliberately triggers dynamic AST syntax ambiguity and raises TypeError on probe inspection
class DefectiveHandler:
    def __init__(self):
        raise TypeError('Inspection forbidden')
    def process(self, val):
        return val
