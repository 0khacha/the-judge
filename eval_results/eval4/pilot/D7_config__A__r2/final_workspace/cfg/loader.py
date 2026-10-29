"""The Config object."""
from .errors import ConfigError
from .interp import expand
from .parser import DEFAULT, parse
from . import types

_MISSING = object()


def _parse_overrides(environ, prefix, sections):
    """Split environment variables into DEFAULT overrides and per-section overrides."""
    head = prefix.upper() + "_"
    default_over = {}
    section_over = {name: {} for name in sections}
    for name, value in environ.items():
        if not name.startswith(head):
            continue
        section, sep, key = name[len(head):].partition("__")
        if not sep or not key:
            continue
        key = key.lower()
        if section.upper() == DEFAULT:
            default_over[key] = value
        for known in sections:
            if known.upper() == section.upper():
                section_over[known][key] = value
    return default_over, section_over


class Config:
    def __init__(self, default, sections, env=None, prefix="APP"):
        self._default = default
        self._sections = sections
        self._environ = dict(env) if env is not None else {}
        self._env_default, self._env_sections = _parse_overrides(
            self._environ, prefix, sections
        )

    @classmethod
    def loads(cls, text, env=None, prefix="APP"):
        default, sections = parse(text)
        return cls(default, sections, env, prefix)

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
        return sorted(
            set(self._default)
            | set(self._env_default)
            | set(self._sections[section])
            | set(self._env_sections[section])
        )

    # -- values ------------------------------------------------------
    def _locate(self, section, key):
        """(raw value, source) of [section] key; KeyError if not defined."""
        over = self._env_sections[section]
        if key in over:
            return over[key], "env"
        own = self._sections[section]
        if key in own:
            return own[key], "file"
        if key in self._env_default:
            return self._env_default[key], "default"
        if key in self._default:
            return self._default[key], "default"
        raise KeyError(key)

    def _raw(self, section, key):
        return self._locate(section, key)[0]

    def source(self, section, key):
        """Where the value of [section] key comes from: 'env', 'file' or 'default'."""
        self._check(section)
        return self._locate(section, key.lower())[1]

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
