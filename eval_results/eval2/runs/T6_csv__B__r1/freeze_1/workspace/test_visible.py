from csvparse import parse_csv

def test_simple():
    assert parse_csv("a,b,c\n1,2,3") == [["a", "b", "c"], ["1", "2", "3"]]

def test_quoted_comma_and_escape():
    assert parse_csv('x,"hello, world","say ""hi"" "') == [["x", "hello, world", 'say "hi" ']]
