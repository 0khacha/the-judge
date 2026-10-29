import pytest

from cfg import Config, ConfigError
from cfg.cli import main

TEXT = """
[DEFAULT]
level = info
host = localhost

[db]
name = app
url = pg://${host}/${name}

[web]
level = debug
"""


def test_section_override_replaces_and_creates_keys():
    env = {"APP_DB__NAME": "other", "APP_DB__NEW__KEY": "x__y"}
    c = Config.loads(TEXT, env=env)
    assert c.get("db", "name") == "other"
    assert c.get("db", "new__key") == "x__y"
    assert c.get("db", "url") == "pg://localhost/other"
    assert "new__key" in c.keys("db")


def test_precedence():
    env = {"APP_DEFAULT__LEVEL": "warn", "APP_WEB__LEVEL": "error"}
    c = Config.loads(TEXT, env=env)
    assert c.get("db", "level") == "warn"      # DEFAULT override beats file DEFAULT
    assert c.get("web", "level") == "error"    # section override wins
    c2 = Config.loads(TEXT, env={"APP_DEFAULT__LEVEL": "warn"})
    assert c2.get("web", "level") == "debug"   # own file value beats DEFAULT override


def test_ignored_variables_and_case_insensitive_section():
    env = {
        "OTHER_DB__NAME": "no",
        "APP_DB": "no",
        "APP_DB__": "no",
        "APP_NOPE__NAME": "no",
        "APP_db__name": "yes",
    }
    c = Config.loads(TEXT, env=env)
    assert c.get("db", "name") == "yes"
    assert c.sections() == ["db", "web"]


def test_custom_prefix():
    c = Config.loads(TEXT, env={"X_DB__NAME": "z"}, prefix="x")
    assert c.get("db", "name") == "z"


def test_env_reference_and_fallback():
    text = "[a]\nset = ${env:HOME_DIR}/x\nfb = ${env:MISSING:-dflt}\nempty = [${env:MISSING:-}]\n"
    c = Config.loads(text, env={"HOME_DIR": "$lit${x}"})
    assert c.get("a", "set") == "$lit${x}/x"
    assert c.get("a", "fb") == "dflt"
    assert c.get("a", "empty") == "[]"


def test_missing_env_raises_on_read_only():
    c = Config.loads("[a]\nx = ${env:NOPE}\n")
    with pytest.raises(ConfigError, match="unknown environment variable NOPE"):
        c.get("a", "x")


def test_empty_override_is_valid():
    c = Config.loads(TEXT, env={"APP_DB__NAME": ""})
    assert c.get("db", "name") == ""


def test_source():
    c = Config.loads(TEXT, env={"APP_WEB__LEVEL": "e", "APP_DEFAULT__HOST": "h"})
    assert c.source("web", "level") == "env"
    assert c.source("db", "name") == "file"
    assert c.source("db", "level") == "default"
    assert c.source("db", "host") == "default"
    with pytest.raises(KeyError):
        c.source("db", "nope")
    with pytest.raises(KeyError):
        c.source("nope", "x")


def test_cli_source_and_prefix(tmp_path, monkeypatch):
    f = tmp_path / "c.ini"
    f.write_text(TEXT, encoding="utf-8")
    monkeypatch.setenv("APP_DB__NAME", "envdb")
    out = []
    assert main(["get", str(f), "db.name"], out.append) == 0
    assert main(["get", "--prefix", "ZZ", str(f), "db.name"], out.append) == 0
    assert main(["get", str(f), "db.name", "--prefix", "ZZ"], out.append) == 0
    assert main(["source", str(f), "db.name"], out.append) == 0
    assert main(["source", str(f), "db.nokey"], out.append) == 1
    assert out == ["envdb", "app", "app", "env", "error: no such key db.nokey"]
    assert main([], out.append) == 2
