import pytest

from cfg import Config, ConfigError
from cfg.cli import main

TEXT = """
# comment
[DEFAULT]
level = info

[db]
host = localhost
name = app
url = postgres://${host}:5432/${name}
ports = 1, 2 ,3
debug = yes

[web]
level = debug
title = a$$b
"""


def test_basic_get_and_default_inheritance():
    c = Config.loads(TEXT)
    assert c.get("db", "host") == "localhost"
    assert c.get("db", "level") == "info"
    assert c.get("web", "level") == "debug"
    assert c.get("db", "zzz", "d") == "d"


def test_interpolation_and_escape():
    c = Config.loads(TEXT)
    assert c.get("db", "url") == "postgres://localhost:5432/app"
    assert c.get("web", "title") == "a$b"


def test_cross_section_reference():
    c = Config.loads("[a]\nx = 1\n[b]\ny = ${a.x}2\n")
    assert c.get("b", "y") == "12"


def test_typed_getters():
    c = Config.loads(TEXT)
    assert c.getlist("db", "ports") == ["1", "2", "3"]
    assert c.getbool("db", "debug") is True
    assert c.getint("db", "missing", 5) == 5
    with pytest.raises(ConfigError):
        c.getint("db", "host")


def test_errors():
    with pytest.raises(ConfigError, match="line 1"):
        Config.loads("x = 1")
    with pytest.raises(ConfigError, match="circular"):
        Config.loads("[a]\nx = ${y}\ny = ${x}\n").get("a", "x")
    with pytest.raises(KeyError):
        Config.loads(TEXT).get("nope", "x")


def test_as_dict_and_sections():
    c = Config.loads(TEXT)
    assert c.sections() == ["db", "web"]
    assert c.as_dict()["web"]["title"] == "a$b"


def test_cli(tmp_path):
    f = tmp_path / "c.ini"
    f.write_text(TEXT, encoding="utf-8")
    out = []
    assert main(["get", str(f), "db.url"], out.append) == 0
    assert out == ["postgres://localhost:5432/app"]
    assert main(["get", str(f), "db.nokey"], out.append) == 1
    assert main([], out.append) == 2
