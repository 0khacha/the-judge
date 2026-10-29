import pytest

from etl import EtlError, parse_spec, run
from etl import writer
from etl.cli import main

SCHEMA = parse_spec("id:int,name:str,joined:date?,active:bool?")

TEXT = """ID, Name ,Joined,Active
1,Ann,2024-01-05,yes
2,Bob,,no
x,Bad,,
3,Cy,2024-13-01,
"""


def test_run_basic():
    res = run(TEXT, SCHEMA)
    assert [r["name"] for r in res.rows] == ["Ann", "Bob"]
    assert res.rows[1]["joined"] is None and res.rows[1]["active"] is False
    assert [r.reason for r in res.rejects] == ["line 4: id: not an int: 'x'", "line 5: joined: not a date: '2024-13-01'"]
    assert (res.stats["read"], res.stats["accepted"], res.stats["rejected"], res.stats["duplicates"]) == (4, 2, 2, 0)


def test_missing_column():
    with pytest.raises(EtlError):
        run("id\n1\n", SCHEMA)


def test_wrong_field_count_and_blank_lines():
    res = run("id,name\n\n1,a\n2\n", parse_spec("id:int,name:str"))
    assert len(res.rows) == 1 and res.rejects[0].reason == "line 4: wrong number of fields"


def test_dedupe_first_and_sort():
    text = "id,name\n2,b\n1,a\n2,c\n"
    res = run(text, parse_spec("id:int,name:str"), key="id")
    assert [r["name"] for r in res.rows] == ["a", "b"]
    assert res.lines == [3, 2]
    assert [r.reason for r in res.rejects] == ["line 4: duplicate of line 2"]
    assert res.stats["duplicates"] == 1 and res.stats["rejected"] == 1


def test_key_validation():
    with pytest.raises(EtlError):
        run("id,name\n1,a\n", parse_spec("id:int,name:str?"), key="name")
    with pytest.raises(EtlError):
        run("id,name\n1,a\n", parse_spec("id:int,name:str"), key="zzz")


def test_writers():
    res = run(TEXT, SCHEMA)
    assert writer.to_csv(res, SCHEMA).splitlines() == ["id,name,joined,active", "1,Ann,2024-01-05,true", "2,Bob,,false"]
    assert writer.to_jsonl(res, SCHEMA).splitlines()[0] == '{"id": 1, "name": "Ann", "joined": "2024-01-05", "active": true}'
    assert writer.rejects_csv(res).splitlines()[0] == "line,reason"


def test_cli():
    out = []
    code = main(["run", "f.csv", "--fields", "id:int,name:str", "--key", "id"], out.append,
                read=lambda p: "id,name\n1,a\n1,b\n")
    assert code == 0
    assert out[0].startswith("read=2 accepted=1 rejected=1 duplicates=1")
    assert out[1:] == ["id,name", "1,a", "! line 3: duplicate of line 2"]
    assert main(["bogus"], out.append) == 2
