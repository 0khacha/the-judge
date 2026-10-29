import pytest

from cfg import Config, ConfigError
from cfg.cli import main

TEXT = """# sample
[DEFAULT]
level = info
region = eu

[db]
host = localhost
port = 5432
url = pg://${host}:${port}

[web]
level = debug
title = Site ${db.host}
"""


def cfg(text=TEXT, **env):
    prefix = env.pop("_prefix", "APP")
    return Config.loads(text, env=env, prefix=prefix)


# ------------------------------------------------------------------ new
def test_new_override_existing_key():
    assert cfg(APP_DB__HOST="h").get("db", "host") == "h"
    assert cfg().get("db", "host") == "localhost"


def test_new_override_creates_key():
    c = cfg(APP_DB__USER="bob")
    assert c.get("db", "user") == "bob"
    assert "user" in c.keys("db") and "user" not in c.keys("web")
    assert c.as_dict()["db"]["user"] == "bob"


def test_new_override_unknown_section_ignored():
    c = cfg(APP_NOPE__X="1")
    assert c.sections() == ["db", "web"] and not c.has_section("NOPE")
    assert c.as_dict() == cfg().as_dict()


def test_new_other_prefix_and_malformed_names_ignored():
    c = cfg(OTHER_DB__HOST="x", APP_DB="y", APP_DB__="z", APPDB__HOST="w", APP__HOST="v")
    assert c.get("db", "host") == "localhost"
    assert c.keys("db") == cfg().keys("db")


def test_new_custom_prefix():
    c = cfg(_prefix="my", MY_DB__HOST="z", APP_DB__PORT="1")
    assert c.get("db", "host") == "z" and c.get("db", "port") == "5432"


def test_new_section_and_key_case_insensitive():
    c = Config.loads(TEXT, env={"APP_Db__Host": "h", "APP_WEB__LEVEL": "warn"})
    assert c.get("db", "host") == "h" and c.get("web", "level") == "warn"
    c2 = Config.loads("[Mixed]\nKey = 1\n", env={"APP_MIXED__KEY": "2"})
    assert c2.get("Mixed", "key") == "2"


def test_new_split_at_first_double_underscore():
    c = cfg(APP_DB__A__B="1")
    assert c.get("db", "a__b") == "1"


def test_new_section_override_beats_own_and_default():
    c = cfg(APP_WEB__LEVEL="warn", APP_DB__LEVEL="trace")
    assert c.get("web", "level") == "warn"
    assert c.get("db", "level") == "trace"


def test_new_default_override_only_supplies_default():
    c = cfg(APP_DEFAULT__LEVEL="trace")
    assert c.get("db", "level") == "trace"
    assert c.get("web", "level") == "debug"


def test_new_default_override_replaces_file_default_and_creates_keys():
    c = cfg(APP_DEFAULT__REGION="us", APP_DEFAULT__EXTRA="e")
    assert c.get("db", "region") == "us" and c.get("web", "region") == "us"
    assert c.get("db", "extra") == "e" and "extra" in c.keys("web")
    assert c.as_dict()["web"]["extra"] == "e"


def test_new_interpolation_sees_overrides_lazily():
    c = cfg(APP_DB__HOST="h")
    assert c.get("db", "url") == "pg://h:5432"
    assert c.get("web", "title") == "Site h"


def test_new_interpolation_sees_default_overrides():
    c = Config.loads("[DEFAULT]\nbase = a\n[s]\nv = ${base}-x\n", env={"APP_DEFAULT__BASE": "b"})
    assert c.get("s", "v") == "b-x"


def test_new_override_values_are_interpolated():
    c = cfg(APP_DB__URL="x-${port}-$$")
    assert c.get("db", "url") == "x-5432-$"


def test_new_override_typed_getters():
    c = cfg(APP_DB__PORT="6000", APP_DB__DEBUG="on", APP_DB__HOSTS="a, b")
    assert c.getint("db", "port") == 6000
    assert c.getbool("db", "debug") is True
    assert c.getlist("db", "hosts") == ["a", "b"]
    bad = cfg(APP_DB__PORT="many")
    with pytest.raises(ConfigError, match="db.port"):
        bad.getint("db", "port")


def test_new_empty_override_is_valid():
    c = cfg(APP_DB__HOST="")
    assert c.get("db", "host") == ""
    assert c.get("db", "url") == "pg://:5432"
    assert c.source("db", "host") == "env"


def test_new_env_reference_in_file_value():
    c = Config.loads("[a]\nx = ${env:HOME_DIR}/bin\n", env={"HOME_DIR": "/h"})
    assert c.get("a", "x") == "/h/bin"


def test_new_env_reference_fallback():
    c = Config.loads("[a]\nx = ${env:NOPE:-dflt}\ny = [${env:NOPE:-}]\nz = ${env:SET:-dflt}\n", env={"SET": "real"})
    assert c.get("a", "x") == "dflt" and c.get("a", "y") == "[]" and c.get("a", "z") == "real"


def test_new_env_reference_missing_raises_on_read_not_load():
    c = Config.loads("[a]\nx = ${env:NOPE}\nok = 1\n", env={})
    assert c.get("a", "ok") == "1"
    with pytest.raises(ConfigError, match="unknown environment variable NOPE"):
        c.get("a", "x")


def test_new_env_reference_without_env_mapping():
    c = Config.loads("[a]\nx = ${env:NOPE}\ny = ${env:NOPE:-d}\n")
    assert c.get("a", "y") == "d"
    with pytest.raises(ConfigError):
        c.get("a", "x")


def test_new_env_reference_inside_override_value():
    c = cfg(APP_DB__HOST="${env:HN}.example", HN="srv")
    assert c.get("db", "host") == "srv.example"
    assert c.get("db", "url") == "pg://srv.example:5432"


def test_new_env_value_used_literally():
    c = Config.loads("[a]\nx = ${env:V}\ny = ${x}!\n", env={"V": "${a.y} $$ ${nothing}"})
    assert c.get("a", "x") == "${a.y} $$ ${nothing}"
    assert c.get("a", "y") == "${a.y} $$ ${nothing}!"


def test_new_dollar_escape_still_works_with_env_syntax():
    c = Config.loads("[a]\nx = $${env:V}\n", env={"V": "q"})
    assert c.get("a", "x") == "${env:V}"


def test_new_source():
    c = cfg(APP_DB__HOST="h", APP_DB__USER="u")
    assert c.source("db", "host") == "env"
    assert c.source("db", "port") == "file"
    assert c.source("db", "level") == "default"
    assert c.source("web", "level") == "file"
    assert c.source("db", "user") == "env"
    assert c.source("db", "HOST") == "env"


def test_new_source_default_override_and_missing():
    c = cfg(APP_DEFAULT__LEVEL="trace", APP_DEFAULT__NEW="n")
    assert c.source("db", "level") == "default" and c.source("db", "new") == "default"
    assert c.source("web", "level") == "file"
    with pytest.raises(KeyError):
        c.source("db", "nokey")
    with pytest.raises(KeyError):
        c.source("nosuch", "x")


def test_new_env_mapping_not_required_to_be_dict():
    from types import MappingProxyType
    c = Config.loads(TEXT, env=MappingProxyType({"APP_DB__HOST": "m"}))
    assert c.get("db", "host") == "m"


@pytest.fixture
def ini(tmp_path):
    f = tmp_path / "c.ini"
    f.write_text(TEXT, encoding="utf-8")
    return str(f)


def test_new_cli_get_uses_environment(ini, monkeypatch):
    monkeypatch.setenv("APP_DB__HOST", "envhost")
    out = []
    assert main(["get", ini, "db.url"], out.append) == 0
    assert out == ["pg://envhost:5432"]


def test_new_cli_show_reflects_overrides(ini, monkeypatch):
    monkeypatch.setenv("APP_WEB__LEVEL", "warn")
    monkeypatch.setenv("APP_DB__USER", "bob")
    out = []
    assert main(["show", ini], out.append) == 0
    assert "level = warn" in out and "user = bob" in out and "level = debug" not in out


def test_new_cli_prefix_option_anywhere(ini, monkeypatch):
    monkeypatch.setenv("XX_DB__HOST", "x")
    monkeypatch.setenv("APP_DB__HOST", "a")
    out = []
    main(["get", ini, "db.host", "--prefix", "xx"], out.append)
    main(["get", "--prefix", "xx", ini, "db.host"], out.append)
    main(["get", ini, "db.host"], out.append)
    assert out == ["x", "x", "a"]


def test_new_cli_source_command(ini, monkeypatch):
    monkeypatch.setenv("APP_DB__HOST", "h")
    out = []
    assert main(["source", ini, "db.host"], out.append) == 0
    assert main(["source", ini, "db.port"], out.append) == 0
    assert main(["source", ini, "db.level"], out.append) == 0
    assert out == ["env", "file", "default"]
    assert main(["source", ini, "db.nokey"], out.append) == 1
    assert out[-1] == "error: no such key db.nokey"
    assert main(["source", ini, "nosuch.x"], out.append) == 1


# ------------------------------------------------------------------ regression
def test_reg_parsing_features():
    c = Config.loads("# c\n; c\n[S]\n  \nKey = v1\nlong = a\n  b\n  c\n")
    assert c.get("S", "key") == "v1"
    assert c.get("S", "long") == "a\nb\nc"
    assert c.get("S", "KEY") == "v1"


@pytest.mark.parametrize("text,line", [
    ("x = 1", "line 1"),
    ("[a]\nnoequals", "line 2"),
    ("[a\nx=1", "line 1"),
    ("[a]\n[a]", "line 2"),
    ("[a]\nx=1\nX=2", "line 3"),
    ("[DEFAULT]\n[DEFAULT]", "line 2"),
    ("[a.b]", "line 1"),
    ("  x = 1", "line 1"),
])
def test_reg_parse_errors(text, line):
    with pytest.raises(ConfigError, match=line):
        Config.loads(text)


def test_reg_default_inheritance_and_keys():
    c = Config.loads(TEXT)
    assert c.get("db", "level") == "info" and c.get("web", "level") == "debug"
    assert c.keys("db") == ["host", "level", "port", "region", "url"]
    assert c.keys("web") == ["level", "region", "title"]
    with pytest.raises(KeyError):
        c.keys("nope")


def test_reg_interpolation_forms():
    c = Config.loads(TEXT)
    assert c.get("db", "url") == "pg://localhost:5432"
    assert c.get("web", "title") == "Site localhost"
    c2 = Config.loads("[DEFAULT]\nd = D\n[s]\nv = ${d}${s.d}${S2.q}\n[S2]\nq = Q\n")
    assert c2.get("s", "v") == "DDQ"


def test_reg_reference_keys_case_insensitive():
    c = Config.loads("[s]\nhost = h\nv = ${HOST}\nw = ${s.Host}\n")
    assert c.get("s", "v") == "h" and c.get("s", "w") == "h"


def test_reg_reference_errors():
    c = Config.loads("[s]\na = ${nope}\nb = ${zz.x}\nc = ${c}\nd = ${e}\ne = ${d}\nf = $x ${\n")
    with pytest.raises(ConfigError, match="unknown reference"):
        c.get("s", "a")
    with pytest.raises(ConfigError, match="unknown reference"):
        c.get("s", "b")
    with pytest.raises(ConfigError, match="circular"):
        c.get("s", "c")
    with pytest.raises(ConfigError, match="circular"):
        c.get("s", "d")
    assert c.get("s", "f") == "$x ${"


def test_reg_dollar_escapes():
    c = Config.loads("[s]\na = $$\nb = a$$b$$$$\nc = $${x}\n")
    assert [c.get("s", k) for k in "abc"] == ["$", "a$b$$", "${x}"]


def test_reg_get_semantics():
    c = Config.loads(TEXT)
    assert c.get("db", "zzz") is None and c.get("db", "zzz", "d") == "d"
    with pytest.raises(KeyError):
        c.get("nope", "x")


def test_reg_typed_getters():
    c = Config.loads("[s]\ni = 7\nf = 1.5\nb1 = YES\nb2 = off\nb3 = maybe\nl = a, ,b ,\ne =\n")
    assert c.getint("s", "i") == 7 and c.getfloat("s", "f") == 1.5
    assert c.getbool("s", "b1") is True and c.getbool("s", "b2") is False
    assert c.getlist("s", "l") == ["a", "b"] and c.getlist("s", "e") == []
    with pytest.raises(ConfigError, match="s.b3"):
        c.getbool("s", "b3")
    with pytest.raises(KeyError):
        c.getint("s", "missing")
    assert c.getint("s", "missing", 3) == 3
    with pytest.raises(ConfigError):
        c.getfloat("s", "b3")


def test_reg_as_dict_and_sections():
    c = Config.loads(TEXT)
    d = c.as_dict()
    assert list(d) == ["db", "web"]
    assert d["web"] == {"level": "debug", "region": "eu", "title": "Site localhost"}
    assert c.has_section("db") and not c.has_section("DEFAULT")


def test_reg_cli_show_and_get(ini):
    out = []
    assert main(["get", ini, "web.title"], out.append) == 0 and out == ["Site localhost"]
    out.clear()
    assert main(["show", ini], out.append) == 0
    assert out[0] == "[db]" and "url = pg://localhost:5432" in out and "[web]" in out


def test_reg_cli_errors(ini, tmp_path):
    out = []
    assert main([], out.append) == 2 and out[-1].startswith("usage:")
    assert main(["bogus", ini], out.append) == 2
    assert main(["get", ini], out.append) == 2
    assert main(["get", ini, "db.nokey"], out.append) == 1
    assert main(["get", str(tmp_path / "missing.ini"), "a.b"], out.append) == 1
    bad = tmp_path / "bad.ini"
    bad.write_text("x = 1", encoding="utf-8")
    assert main(["show", str(bad)], out.append) == 1 and "line 1" in out[-1]
