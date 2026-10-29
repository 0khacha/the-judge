import os, json
from _h import *
T = "D7_config"
r = mk(T, "reference")
p = lambda *a: os.path.join(r, *a)
L = p("cfg/loader.py")
rep(L, '''    def __init__(self, default, sections):
        self._default = default
        self._sections = sections

    @classmethod
    def loads(cls, text):
        default, sections = parse(text)
        return cls(default, sections)
''', '''    def __init__(self, default, sections, env=None, prefix="APP"):
        self._default = default
        self._sections = sections
        self._env = dict(env) if env is not None else {}
        self._over = {}
        self._read_overrides(prefix)

    @classmethod
    def loads(cls, text, env=None, prefix="APP"):
        default, sections = parse(text)
        return cls(default, sections, env, prefix)

    def _read_overrides(self, prefix):
        lead = prefix.upper() + "_"
        names = {name.upper(): name for name in self._sections}
        names.setdefault("DEFAULT", "DEFAULT")
        for var in sorted(self._env):
            if not var.startswith(lead):
                continue
            section, sep, key = var[len(lead):].partition("__")
            if not sep or not key or section.upper() not in names:
                continue
            self._over.setdefault(names[section.upper()], {})[key.lower()] = self._env[var]

    def env_value(self, name, fallback=None):
        if name in self._env:
            return self._env[name]
        if fallback is not None:
            return fallback
        raise ConfigError("unknown environment variable %s" % name)
''')
rep(L, '''        return sorted(set(self._default) | set(self._sections[section]))''', '''        found = set(self._default) | set(self._sections[section])
        found |= set(self._over.get(section, {})) | set(self._over.get("DEFAULT", {}))
        return sorted(found)''')
rep(L, '''    def _raw(self, section, key):
        own = self._sections[section]
        if key in own:
            return own[key]
        if key in self._default:
            return self._default[key]
        raise KeyError(key)
''', '''    def _lookup(self, section, key):
        """(raw value, source) following the precedence rules."""
        over = self._over.get(section, {})
        if key in over:
            return over[key], "env"
        own = self._sections[section]
        if key in own:
            return own[key], "file"
        over_default = self._over.get("DEFAULT", {})
        if key in over_default:
            return over_default[key], "default"
        if key in self._default:
            return self._default[key], "default"
        raise KeyError(key)

    def _raw(self, section, key):
        return self._lookup(section, key)[0]

    def source(self, section, key):
        self._check(section)
        return self._lookup(section, key.lower())[1]
''')
I = p("cfg/interp.py")
rep(I, '''        name = name.strip()
        if "." in name:''', '''        name = name.strip()
        if name.startswith("env:"):
            var, sep, fallback = name[4:].partition(":-")
            return config.env_value(var.strip(), fallback if sep else None)
        if "." in name:''')
C = p("cfg/cli.py")
rep(C, '''import sys
''', '''import os
import sys
''')
rep(C, '''def _load(path):
    with open(path, encoding="utf-8") as fh:
        return Config.loads(fh.read())
''', '''def _load(path, prefix):
    with open(path, encoding="utf-8") as fh:
        return Config.loads(fh.read(), env=os.environ, prefix=prefix)


def _split_prefix(argv):
    """Remove `--prefix P` from argv; returns (rest, prefix)."""
    rest, prefix, i = [], "APP", 0
    while i < len(argv):
        if argv[i] == "--prefix" and i + 1 < len(argv):
            prefix = argv[i + 1]
            i += 2
        else:
            rest.append(argv[i])
            i += 1
    return rest, prefix
''')
rep(C, '''    if len(argv) < 2 or argv[0] not in ("show", "get"):
        out("usage: cfg show FILE | cfg get FILE section.key")
        return 2
    try:
        config = _load(argv[1])''', '''    argv, prefix = _split_prefix(argv)
    if len(argv) < 2 or argv[0] not in ("show", "get", "source"):
        out("usage: cfg show FILE | cfg get FILE section.key | cfg source FILE section.key")
        return 2
    try:
        config = _load(argv[1], prefix)''')
rep(C, '''        else:
            if len(argv) != 3 or "." not in argv[2]:
                out("usage: cfg get FILE section.key")
                return 2
            section, _, key = argv[2].partition(".")
            value = config.get(section, key, None)
            if value is None:
                out("error: no such key %s" % argv[2])
                return 1
            out(value)''', '''        else:
            if len(argv) != 3 or "." not in argv[2]:
                out("usage: cfg %s FILE section.key" % argv[0])
                return 2
            section, _, key = argv[2].partition(".")
            if argv[0] == "source":
                try:
                    out(config.source(section, key))
                except KeyError:
                    out("error: no such key %s" % argv[2])
                    return 1
                return 0
            value = config.get(section, key, None)
            if value is None:
                out("error: no such key %s" % argv[2])
                return 1
            out(value)''')
rep(C, '"""python -m cfg.cli show FILE | get FILE section.key"""', '"""python -m cfg.cli show FILE | get FILE section.key | source FILE section.key"""')
w = clone(T, "reference", "wrong_1")   # keys() ignores env-created keys; CLI ignores the environment
rep(os.path.join(w, "cfg/loader.py"), '        found |= set(self._over.get(section, {})) | set(self._over.get("DEFAULT", {}))\n', '')
rep(os.path.join(w, "cfg/cli.py"), "env=os.environ, prefix=prefix", "prefix=prefix")
w = clone(T, "reference", "wrong_2")   # references became case-sensitive
rep(os.path.join(w, "cfg/interp.py"), "        target_key = target_key.lower()\n", "")
json.dump({"task": T, "lines": 0, "change_requirements": 7, "traps": [
 "DEFAULT override must not beat a section's own value",
 "overrides applied lazily so interpolated references see them (including cross-section)",
 "keys()/as_dict() include override-created keys (loader)",
 "${env:..:-fallback} parsing, error on read not load",
 "CLI must read os.environ, --prefix anywhere, source command",
 "section matching case-insensitive; first __ split",
 "regression: case-insensitive references, parser errors, circular detection"]}, open(os.path.join(H, T, "label.json"), "w"), indent=1)
