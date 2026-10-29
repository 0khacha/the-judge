"""The Config object."""
from .errors import ConfigError
from .interp import expand
from .parser import parse
from . import types

_MISSING = object()


class Config:
    def __init__(self, default, sections):
        self._default = default
        self._sections = sections

    @classmethod
    def loads(cls, text):
        default, sections = parse(text)
        return cls(default, sections)

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
        return sorted(set(self._default) | set(self._sections[section]))

    # -- values ------------------------------------------------------
    def _raw(self, section, key):
        own = self._sections[section]
        if key in own:
            return own[key]
        if key in self._default:
            return self._default[key]
        raise KeyError(key)

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
