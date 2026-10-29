import pytest

from cfg import Config, ConfigError
from cfg.cli import main

TEXT = "[DEFAULT]\nlevel = info\n[db]\nhost = localhost\nname = app\nurl = pg://${host}/${name}\n[web]\nlevel = debug\n"


def test_section_override_replaces_and_propagates():
    c = Config.loads(TEXT, env={"APP_DB__HOST": "h2"})
    assert c.get("db", "host") == "h2"
    assert c.get("db", "url") == "pg://h2/app"
    assert c.source("db", "host") == "env"


def test_section_name_case_insensitive_and_new_key():
    c = Config.loads(TEXT, env={"APP_DB__Extra": "x"})
    assert c.get("db", "extra") == "x"
    assert "extra" in c.keys("db")


def test_default_override_precedence():
    c = Config.loads(TEXT, env={"APP_DEFAULT__LEVEL": "warn", "APP_DEFAULT__new": "n"})
    assert c.get("db", "level") == "warn"
    assert c.get("web", "level") == "debug"
    assert c.source("db", "level") == "default"
    assert c.source("web", "level") == "file"
    assert c.get("db", "new") == "n"


def test_ignored_variables():
    env = {"OTHER_DB__HOST": "x", "APP_DB": "x", "APP_DB__": "x", "APP_NOPE__HOST": "x"}
    c = Config.loads(TEXT, env=env)
    assert c.get("db", "host") == "localhost"
    assert c.keys("db") == ["host", "level", "name", "url"]


def test_custom_prefix_and_empty_value():
    c = Config.loads(TEXT, env={"X_DB__HOST": ""}, prefix="x")
    assert c.get("db", "host") == ""


def test_env_reference_and_literal_substitution():
    text = "[a]\nv = ${env:TOKEN}\nw = ${env:MISSING:-fb}\nz = ${env:EMPTY:-}\n"
    c = Config.loads(text, env={"TOKEN": "$${a.w}"})
    assert c.get("a", "v") == "$${a.w}"
    assert c.get("a", "w") == "fb"
    assert c.get("a", "z") == ""


def test_env_missing_raises_on_read():
    c = Config.loads("[a]\nv = ${env:NOPE}\n")
    with pytest.raises(ConfigError, match="unknown environment variable NOPE"):
        c.get("a", "v")


def test_source_errors():
    c = Config.loads(TEXT)
    with pytest.raises(KeyError):
        c.source("nope", "host")
    with pytest.raises(KeyError):
        c.source("db", "nope")


def test_cli_source_and_prefix(tmp_path, monkeypatch):
    f = tmp_path / "c.ini"
    f.write_text(TEXT, encoding="utf-8")
    monkeypatch.setenv("MY_DB__HOST", "envhost")
    out = []
    assert main(["source", str(f), "db.host", "--prefix", "MY"], out.append) == 0
    assert main(["get", "--prefix", "MY", str(f), "db.host"], out.append) == 0
    assert main(["source", str(f), "db.zzz"], out.append) == 1
    assert out == ["env", "envhost", "error: no such key db.zzz"]
    assert main(["source", str(f), "--prefix"], out.append) == 2
