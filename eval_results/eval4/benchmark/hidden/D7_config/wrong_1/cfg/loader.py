"""The Config object."""
from .errors import ConfigError
from .interp import expand
from .parser import parse
from . import types

_MISSING = object()


class Config:
    def __init__(self, default, sections, env=None, prefix="APP"):
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

    # -- structure ---------------------------------------------------
    def has_section(self, section):
        return section in self._sections

    def sections(self):
        return list(self._sections)

    def _check(self, section):
        if section not in self._sections:
            raise KeyError(section)

    def keys(self, section):
        self._check(section)
        found = set(self._default) | set(self._sections[section])
        return sorted(found)

    # -- values ------------------------------------------------------
    def _lookup(self, section, key):
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

    def resolve(self, section, key, stack=()):
        """Fully expanded value of [section] key (KeyError if missing)."""
        raw = self._raw(section, key)
        marker = (section, key)
        if marker in stack:
            chain = " -> ".join("%s.%s" % pair for pair in list(stack) + [marker])
            raise ConfigError("circular reference: %s" % chain)
        return expand(self, section, key, raw, tuple(stack) + (marker,))

    def get(self, section, key, default=None):
        self._check(section)
        try:
            return self.resolve(section, key.lower())
        except KeyError:
            return default

    def _typed(self, convert, section, key, default):
        value = self.get(section, key, _MISSING)
        if value is _MISSING:
            if default is _MISSING:
                raise KeyError("%s.%s" % (section, key))
            return default
        return convert(value, "%s.%s" % (section, key))

    def getint(self, section, key, default=_MISSING):
        return self._typed(types.to_int, section, key, default)

    def getfloat(self, section, key, default=_MISSING):
        return self._typed(types.to_float, section, key, default)

    def getbool(self, section, key, default=_MISSING):
        return self._typed(types.to_bool, section, key, default)

    def getlist(self, section, key, default=_MISSING):
        return self._typed(types.to_list, section, key, default)

    def as_dict(self):
        return {s: {k: self.resolve(s, k) for k in self.keys(s)} for s in self._sections}
