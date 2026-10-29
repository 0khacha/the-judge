from csvparse import parse_csv, parse_csv_dicts, CsvError


def test_simple():
    assert parse_csv("a,b\n1,2\n") == [["a", "b"], ["1", "2"]]


def test_quoted():
    assert parse_csv('"x,y","he said ""hi"""') == [["x,y", 'he said "hi"']]


def test_dicts():
    assert parse_csv_dicts("n,v\na,1\n") == [{"n": "a", "v": "1"}]
