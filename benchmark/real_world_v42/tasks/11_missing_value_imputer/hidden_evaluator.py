from missing_value_imputer import MissingValueImputer

def evaluate():
    imp = MissingValueImputer()
    
    # ffill test
    res = imp.impute([None, 5, None, None, 12], strategy="ffill")
    assert res == [None, 5, 5, 5, 12], f"Expected [None, 5, 5, 5, 12], got {res}"
    
    # mean test
    res_m = imp.impute([10, None, 30], strategy="mean")
    assert res_m == [10, 20.0, 30]
    return True
