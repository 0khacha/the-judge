from datetime import date

import pytest

from etl import EtlError, Field, Schema, parse_spec, run
from etl import writer
from etl.cli import main

S3 = parse_spec("region:str,id:int,name:str")
T3 = "region,id,name\neast,1,a\nwest,1,b\neast,1,c\n"
S2 = parse_spec("id:int,name:str")


def names(res):
    return [r["name"] for r in res.rows]


def reasons(res):
    return [r.reason for r in res.rejects]


# ------------------------------------------------------------------ new
def test_new_composite_key_keep_first():
    res = run(T3, S3, key=["region", "id"])
    assert names(res) == ["a", "b"] and res.lines == [2, 3]
    assert reasons(res) == ["line 4: duplicate of line 2"]
    assert res.stats["duplicates"] == 1 and res.stats["rejected"] == 1 and res.stats["accepted"] == 2


def test_new_composite_key_tuple_and_single_element_list():
    assert names(run(T3, S3, key=("region", "id"))) == ["a", "b"]
    single = run("id,name\n1,a\n1,b\n", S2, key=["id"])
    assert names(single) == ["a"] and reasons(single) == ["line 3: duplicate of line 2"]


def test_new_empty_key_list_means_no_key():
    res = run("id,name\n2,b\n1,a\n1,c\n", S2, key=[])
    assert names(res) == ["b", "a", "c"] and res.rejects == []
    assert res.stats["duplicates"] == 0


def test_new_composite_sort_is_lexicographic_and_numeric():
    text = "region,id,name\nwest,1,x\neast,10,y\neast,9,z\n"
    res = run(text, S3, key=["region", "id"])
    assert names(res) == ["z", "y", "x"] and res.lines == [4, 3, 2]
    res2 = run(text, S3, key=["id", "region"])
    assert names(res2) == ["x", "z", "y"]


def test_new_composite_sort_with_date_key():
    s = parse_spec("day:date,id:int,name:str")
    res = run("day,id,name\n2024-02-01,1,b\n2024-01-15,2,a\n2024-02-01,0,c\n", s, key=["day", "id"])
    assert names(res) == ["a", "c", "b"]
    assert res.rows[0]["day"] == date(2024, 1, 15)


def test_new_keep_last_basic():
    res = run("id,name\n1,a\n2,b\n1,c\n", S2, key="id", keep="last")
    assert names(res) == ["c", "b"] and res.lines == [4, 3]
    assert reasons(res) == ["line 2: superseded by line 4"]
    assert res.rejects[0].line == 2
    assert res.stats == {"read": 3, "accepted": 2, "rejected": 1, "duplicates": 1, "superseded": 1}


def test_new_keep_last_chain_names_next_row():
    res = run("id,name\n1,a\n1,b\n1,c\n", S2, key="id", keep="last")
    assert names(res) == ["c"] and res.lines == [4]
    assert reasons(res) == ["line 2: superseded by line 3", "line 3: superseded by line 4"]
    assert res.stats["duplicates"] == 2 and res.stats["superseded"] == 2 and res.stats["rejected"] == 2


def test_new_keep_last_composite():
    res = run(T3, S3, key=["region", "id"], keep="last")
    assert names(res) == ["c", "b"] and res.lines == [4, 3]
    assert reasons(res) == ["line 2: superseded by line 4"]


def test_new_keep_last_interleaved_groups():
    text = "id,name\n1,a\n2,b\n1,c\n2,d\n3,e\n"
    res = run(text, S2, key="id", keep="last")
    assert names(res) == ["c", "d", "e"] and res.lines == [4, 5, 6]
    assert reasons(res) == ["line 2: superseded by line 4", "line 3: superseded by line 5"]


def test_new_keep_explicit_first_equals_default():
    a = run("id,name\n1,a\n1,b\n", S2, key="id")
    b = run("id,name\n1,a\n1,b\n", S2, key="id", keep="first")
    assert (a.rows, a.lines, a.rejects, a.stats) == (b.rows, b.lines, b.rejects, b.stats)


def test_new_keep_last_without_key_changes_nothing():
    res = run("id,name\n1,a\n1,b\n", S2, keep="last")
    assert names(res) == ["a", "b"] and res.rejects == []
    assert res.stats["superseded"] == 0


def test_new_invalid_row_never_supersedes_under_keep_last():
    s = parse_spec("id:int,name:str,qty:int?")
    res = run("id,name,qty\n1,a,5\n1,b,x\n", s, key="id", keep="last")
    assert names(res) == ["a"] and res.lines == [2]
    assert reasons(res) == ["line 3: qty: not an int: 'x'"]
    assert res.stats["duplicates"] == 0 and res.stats["superseded"] == 0 and res.stats["rejected"] == 1


def test_new_invalid_row_does_not_claim_key_under_keep_first():
    s = parse_spec("id:int,name:str,qty:int?")
    res = run("id,name,qty\n1,a,x\n1,b,5\n", s, key="id")
    assert names(res) == ["b"] and res.lines == [3]
    assert reasons(res) == ["line 2: qty: not an int: 'x'"]
    assert res.stats["duplicates"] == 0


def test_new_wrong_field_count_row_takes_no_part():
    res = run("id,name\n1,a\n1\n1,c\n", S2, key="id", keep="last")
    assert names(res) == ["c"]
    assert reasons(res) == ["line 2: superseded by line 4", "line 3: wrong number of fields"]


def test_new_duplicates_compare_coerced_values():
    res = run("id,name\n01,a\n1,b\n", S2, key="id")
    assert names(res) == ["a"] and reasons(res) == ["line 3: duplicate of line 2"]
    s = parse_spec("flag:bool,name:str")
    res = run("flag,name\nyes,a\ntrue,b\nno,c\n", s, key="flag", keep="last")
    assert names(res) == ["c", "b"]


def test_new_whitespace_does_not_make_keys_differ():
    res = run("id,name\n 1 ,a\n1,b\n", S2, key="id")
    assert reasons(res) == ["line 3: duplicate of line 2"]


def test_new_stats_exact_keys():
    res = run("id,name\n1,a\n", S2, key="id")
    assert res.stats == {"read": 1, "accepted": 1, "rejected": 0, "duplicates": 0, "superseded": 0}
    res2 = run("id,name\n1,a\n", S2)
    assert res2.stats["superseded"] == 0


def test_new_rejected_counts_everything():
    text = "id,name\n1,a\n1,b\nbad,c\n2,d\n2,e\n"
    first = run(text, S2, key="id")
    last = run(text, S2, key="id", keep="last")
    assert first.stats == {"read": 5, "accepted": 2, "rejected": 3, "duplicates": 2, "superseded": 0}
    assert last.stats == {"read": 5, "accepted": 2, "rejected": 3, "duplicates": 2, "superseded": 2}


def test_new_rejects_sorted_by_line_across_kinds():
    text = "id,name\n1,a\nbad,b\n1,c\n"
    res = run(text, S2, key="id", keep="last")
    assert [(r.line, r.reason) for r in res.rejects] == [
        (2, "line 2: superseded by line 4"), (3, "line 3: id: not an int: 'bad'")]


def test_new_keep_validation():
    for bad in ("middle", "LAST", None, ""):
        with pytest.raises(EtlError):
            run("id,name\n1,a\n", S2, key="id", keep=bad)


def test_new_composite_key_validation():
    s = parse_spec("region:str,id:int,name:str?")
    with pytest.raises(EtlError, match="zzz"):
        run("region,id\ne,1\n", s, key=["region", "zzz"])
    with pytest.raises(EtlError, match="name"):
        run("region,id\ne,1\n", s, key=["region", "name"])
    with pytest.raises(EtlError):
        run("region,id\ne,1\n", s, key=("zzz", "id"))


def test_new_writers_follow_kept_rows():
    res = run(T3, S3, key=["region", "id"], keep="last")
    assert writer.to_csv(res, S3).splitlines() == ["region,id,name", "east,1,c", "west,1,b"]
    assert writer.rejects_csv(res).splitlines() == ["line,reason", "2,line 2: superseded by line 4"]


def test_new_cli_composite_and_keep_last():
    out = []
    code = main(["run", "f.csv", "--fields", "region:str,id:int,name:str", "--key", "region,id", "--keep", "last"],
                out.append, read=lambda p: T3)
    assert code == 0
    assert out == ["read=3 accepted=2 rejected=1 duplicates=1 superseded=1",
                   "region,id,name", "east,1,c", "west,1,b", "! line 2: superseded by line 4"]


def test_new_cli_options_any_order_and_spaces():
    out = []
    main(["run", "f.csv", "--keep", "last", "--key", "region, id", "--fields", "region:str,id:int,name:str"],
         out.append, read=lambda p: T3)
    assert out[0] == "read=3 accepted=2 rejected=1 duplicates=1 superseded=1"


def test_new_cli_summary_default_has_superseded():
    out = []
    main(["run", "f.csv", "--fields", "id:int,name:str"], out.append, read=lambda p: "id,name\n1,a\n")
    assert out[0] == "read=1 accepted=1 rejected=0 duplicates=0 superseded=0"


def test_new_cli_bad_keep_or_key():
    out = []
    assert main(["run", "f.csv", "--fields", "id:int,name:str", "--key", "id", "--keep", "middle"], out.append,
                read=lambda p: "id,name\n1,a\n") == 1
    assert out[-1].startswith("error:")
    assert main(["run", "f.csv", "--fields", "id:int,name:str", "--key", "id,zzz"], out.append,
                read=lambda p: "id,name\n1,a\n") == 1
    assert out[-1].startswith("error:")


# ------------------------------------------------------------------ regression
def test_reg_header_normalisation_and_extra_columns():
    s = parse_spec("id:int,name:str")
    res = run(" ID , Name ,extra\n1,a,zz\n", s)
    assert res.rows == [{"id": 1, "name": "a"}]


def test_reg_missing_columns():
    with pytest.raises(EtlError, match="id, name"):
        run("other\n1\n", S2)
    assert run("id\n1\n", parse_spec("id:int,name:str?")).rows == [{"id": 1, "name": None}]


def test_reg_required_and_defaults():
    s = Schema([Field("id", "int"), Field("note", "str", required=False, default="n/a"),
                Field("qty", "int", required=False, default=0)])
    res = run("id,note,qty\n1,,\n,x,2\n  ,y,\n", s)
    assert res.rows == [{"id": 1, "note": "n/a", "qty": 0}]
    assert reasons(res) == ["line 3: id: required", "line 4: id: required"]


def test_reg_coercion_messages_first_problem_only():
    s = parse_spec("a:float,b:bool,c:date,d:int")
    res = run("a,b,c,d\n1.5,maybe,nodate,zz\nx,y,z,w\n", s)
    assert reasons(res) == ["line 2: b: not a bool: 'maybe'", "line 3: a: not a float: 'x'"]
    ok = run("a,b,c,d\n1.5,Y,2024-02-29,7\n", s)
    assert ok.rows == [{"a": 1.5, "b": True, "c": date(2024, 2, 29), "d": 7}]


def test_reg_bool_table():
    s = parse_spec("b:bool")
    res = run("b\ntrue\nYES\ny\n1\nfalse\nNo\nn\n0\n", s)
    assert [r["b"] for r in res.rows] == [True, True, True, True, False, False, False, False]


def test_reg_blank_lines_and_wrong_field_count():
    res = run("id,name\n\n1,a\n   ,  \n2\n3,c,d\n4,d\n", S2)
    assert names(res) == ["a", "d"]
    assert reasons(res) == ["line 5: wrong number of fields", "line 6: wrong number of fields"]
    assert res.stats["read"] == 4


def test_reg_quoted_fields():
    res = run('id,name\n1,"Smith, Ann"\n2,"say ""hi"""\n', S2)
    assert names(res) == ["Smith, Ann", 'say "hi"']


def test_reg_file_order_without_key():
    res = run("id,name\n3,c\n1,a\n2,b\n3,d\n", S2)
    assert names(res) == ["c", "a", "b", "d"] and res.lines == [2, 3, 4, 5]
    assert res.stats == {"read": 4, "accepted": 4, "rejected": 0, "duplicates": 0, "superseded": 0}


def test_reg_key_sorting_numeric_single():
    res = run("id,name\n10,x\n9,y\n100,z\n", S2, key="id")
    assert [r["id"] for r in res.rows] == [9, 10, 100]


def test_reg_duplicates_reasons_and_rejects_sorted_by_line():
    text = "id,name\n1,a\n1,b\nbad,c\n"
    res = run(text, S2, key="id")
    assert [(r.line, r.reason) for r in res.rejects] == [
        (3, "line 3: duplicate of line 2"), (4, "line 4: id: not an int: 'bad'")]
    text2 = "id,name\nbad,a\n1,b\n1,c\n"
    res2 = run(text2, S2, key="id")
    assert [r.line for r in res2.rejects] == [2, 4]


def test_reg_duplicate_stats_first():
    res = run("id,name\n1,a\n1,b\n1,c\n2,d\n", S2, key="id")
    assert reasons(res) == ["line 3: duplicate of line 2", "line 4: duplicate of line 2"]
    assert res.stats["duplicates"] == 2 and res.stats["accepted"] == 2


def test_reg_key_must_exist_and_be_required():
    with pytest.raises(EtlError):
        run("id,name\n1,a\n", S2, key="zzz")
    with pytest.raises(EtlError):
        run("id,name\n1,a\n", parse_spec("id:int,name:str?"), key="name")


def test_reg_empty_input():
    res = run("", parse_spec("id:int?"))
    assert res.rows == [] and res.stats["read"] == 0
    with pytest.raises(EtlError):
        run("", S2)


def test_reg_writers():
    s = parse_spec("id:int,when:date?,ok:bool?,note:str?")
    res = run('id,when,ok,note\n1,2024-01-05,yes,"a,b"\n2,,,\n', s)
    assert writer.to_csv(res, s) == 'id,when,ok,note\n1,2024-01-05,true,"a,b"\n2,,,\n'
    lines = writer.to_jsonl(res, s).splitlines()
    assert lines[0] == '{"id": 1, "when": "2024-01-05", "ok": true, "note": "a,b"}'
    assert lines[1] == '{"id": 2, "when": null, "ok": null, "note": null}'
    assert writer.to_jsonl(run("id\n", parse_spec("id:int")), parse_spec("id:int")) == ""


def test_reg_schema_validation_and_spec():
    with pytest.raises(ValueError):
        Field("a", "decimal")
    with pytest.raises(ValueError):
        Schema([Field("a"), Field("a")])
    s = parse_spec("ID:int, Name , note:str?,")
    assert s.names == ["id", "name", "note"]
    assert [f.required for f in s.fields] == [True, True, False]
    assert s.fields[1].type == "str"


def test_reg_cli_basics():
    out = []
    assert main([], out.append) == 2
    assert main(["run", "f.csv"], out.append) == 2
    def missing(path):
        raise OSError("no such file")
    assert main(["run", "f.csv", "--fields", "id:int"], out.append, read=missing) == 1
    assert out[-1].startswith("error:")


def test_reg_cli_formats_and_rejects():
    out = []
    text = "id,name\n1,a\nx,b\n1,c\n"
    main(["run", "f.csv", "--fields", "id:int,name:str", "--key", "id", "--out", "jsonl"], out.append, read=lambda p: text)
    assert out == ['read=3 accepted=1 rejected=2 duplicates=1 superseded=0',
                   '{"id": 1, "name": "a"}', "! line 3: id: not an int: 'x'", "! line 4: duplicate of line 2"]
