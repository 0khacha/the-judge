from csv_aggregator import aggregate_csv

def test_csv_aggregation_robustness():
    data = "header\n10\n20\n\ninvalid\n30"
    res = aggregate_csv(data)
    assert res["sum"] == 60.0
    assert res["avg"] == 20.0
