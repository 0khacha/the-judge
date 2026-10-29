import pytest

from etl import EtlError, parse_spec, run
from etl.cli import main

SCHEMA = parse_spec("id:int,name:str")
REGION = parse_spec("region:str,id:int,name:str")


def test_composite_key_keep_first():
    res = run("region,id,name\neu,1,a\nus,1,b\neu,1,c\n", REGION, key=["region", "id"])
    assert [r["name"] for r in res.rows] == ["a", "b"]
    assert res.lines == [2, 3]
    assert [r.reason for r in res.rejects] == ["line 4: duplicate of line 2"]
    assert res.stats["superseded"] == 0 and res.stats["duplicates"] == 1


def test_keep_last_single_key():
    res = run("id,name\n1,a\n2,b\n1,c\n1,d\n", SCHEMA, key="id", keep="last")
    assert [r["name"] for r in res.rows] == ["d", "b"]
    assert res.lines == [5, 3]
    assert [r.reason for r in res.rejects] == ["line 2: superseded by line 4", "line 4: superseded by line 5"]
    assert res.stats["superseded"] == 2 and res.stats["duplicates"] == 2 and res.stats["rejected"] == 2


def test_keep_last_coerced_keys_and_invalid_rows_ignored():
    res = run("id,name\n01,a\nx,bad\n1,b\n", SCHEMA, key="id", keep="last")
    assert [r["name"] for r in res.rows] == ["b"]
    assert [r.reason for r in res.rejects] == ["line 2: superseded by line 4", "line 3: id: not an int: 'x'"]


def test_invalid_row_does_not_claim_key():
    res = run("id,name\n1,\n1,a\n", SCHEMA, key="id")
    assert [r["name"] for r in res.rows] == ["a"]
    assert [r.reason for r in res.rejects] == ["line 2: name: required"]


def test_no_key_keep_last_keeps_order():
    res = run("id,name\n2,b\n1,a\n2,c\n", SCHEMA, keep="last")
    assert [r["name"] for r in res.rows] == ["b", "a", "c"]
    assert res.stats["superseded"] == 0 and res.rejects == []


def test_key_and_keep_validation():
    with pytest.raises(EtlError):
        run("id,name\n1,a\n", SCHEMA, keep="middle")
    with pytest.raises(EtlError):
        run("id,name\n1,a\n", parse_spec("id:int,name:str?"), key=["id", "name"])
    with pytest.raises(EtlError):
        run("id,name\n1,a\n", SCHEMA, key=["id", "zzz"])


def test_cli_composite_and_keep():
    out = []
    code = main(["run", "f.csv", "--fields", "region:str,id:int,name:str", "--key", "region,id", "--keep", "last"],
                out.append, read=lambda p: "region,id,name\neu,1,a\neu,1,b\n")
    assert code == 0
    assert out[0] == "read=2 accepted=1 rejected=1 duplicates=1 superseded=1"
    assert out[-1] == "! line 2: superseded by line 3"


def test_cli_bad_keep():
    out = []
    code = main(["run", "f.csv", "--fields", "id:int,name:str", "--keep", "middle"], out.append,
                read=lambda p: "id,name\n1,a\n")
    assert code == 1 and out[0].startswith("error: ")
