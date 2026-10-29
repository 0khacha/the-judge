"""The Config object."""
from .errors import ConfigError
from .interp import expand
from .parser import DEFAULT, parse
from . import types

_MISSING = object()


def _env_overrides(env, prefix, section_names):
    """Split `env` into DEFAULT overrides and per-section overrides.

    Variables look like <PREFIX>_<SECTION>__<KEY>; the name is split at the
    first "__" after the prefix. Anything else is ignored.
    """
    default_over = {}
    section_over = {name: {} for name in section_names}
    head = prefix.upper() + "_"
    for name, value in env.items():
        if not name.startswith(head):
            continue
        section, sep, key = name[len(head):].partition("__")
        if not sep or not key:
            continue
        key = key.lower()
        if section.upper() == DEFAULT:
            default_over[key] = value
            continue
        for target in section_names:
            if target.upper() == section.upper():
                section_over[target][key] = value
    return default_over, section_over


class Config:
    def __init__(self, default, sections, env=None, prefix="APP"):
        self._default = default
        self._sections = sections
        self._env = dict(env) if env else {}
        self._env_default, self._env_sections = _env_overrides(
            self._env, prefix, list(sections))

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
        names = (set(self._default) | set(self._env_default)
                 | set(self._sections[section]) | set(self._env_sections[section]))
        return sorted(names)

    # -- environment -------------------------------------------------
    def env_var(self, name):
        """Value of environment variable `name`, or None if not set."""
        return self._env.get(name)

    # -- values ------------------------------------------------------
    def _locate(self, section, key):
        """(source, raw value) of [section] key; KeyError if missing."""
        over = self._env_sections[section]
        if key in over:
            return "env", over[key]
        own = self._sections[section]
        if key in own:
            return "file", own[key]
        if key in self._env_default:
            return "default", self._env_default[key]
        if key in self._default:
            return "default", self._default[key]
        raise KeyError(key)

    def source(self, section, key):
        """'env', 'file' or 'default' for [section] key."""
        self._check(section)
        return self._locate(section, key.lower())[0]

    def resolve(self, section, key, stack=()):
        """Fully expanded value of [section] key (KeyError if missing)."""
        _, raw = self._locate(section, key)
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
