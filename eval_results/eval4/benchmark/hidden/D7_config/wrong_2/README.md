# cfg - INI-style configuration with interpolation

```
[DEFAULT]
level = info

[db]
host = localhost
url = postgres://${host}:5432/${name}
name = app
```

* `[section]` headers (no dots in names), `key = value` lines (keys are lower-cased, values stripped), `#` and `;` comment lines, indented lines continue the previous value (joined with a newline).
  Errors are `ConfigError("line N: ...")`: key outside a section, line without `=`, bad header, duplicate section, duplicate key.
* `[DEFAULT]` values are inherited by every section; a section's own value wins.
* Interpolation (done when a value is read): `${key}` (same section, then DEFAULT), `${section.key}`, `$$` for a literal `$`. Unknown references and circular references raise `ConfigError`.
* `Config.loads(text)`; `get(section, key, default=None)` (unknown section: `KeyError`, missing key: `default`), `getint`, `getfloat`, `getbool` (`true/false/yes/no/on/off/1/0`), `getlist` (comma separated), `sections()`, `keys(section)`, `as_dict()` (all values resolved, DEFAULT merged in), `has_section`.
* `python -m cfg.cli show FILE` / `get FILE section.key`.
