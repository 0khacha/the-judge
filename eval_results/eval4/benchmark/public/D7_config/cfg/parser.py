"""Text -> (default values, ordered sections of raw values)."""
import re
from collections import OrderedDict

from .errors import ConfigError

DEFAULT = "DEFAULT"
SECTION_RE = re.compile(r"^\[([^\].\s][^\].]*)\]$")


def parse(text):
    default = {}
    sections = OrderedDict()
    current = None          # dict being filled
    last_key = None
    seen_default = False
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped[0] in "#;":
            continue
        if raw[0] in " \t":
            if current is None or last_key is None:
                raise ConfigError("line %d: continuation without a value" % number)
            current[last_key] += "\n" + stripped
            continue
        if stripped.startswith("["):
            m = SECTION_RE.match(stripped)
            if not m:
                raise ConfigError("line %d: bad section header %r" % (number, stripped))
            name = m.group(1).strip()
            if name == DEFAULT:
                if seen_default:
                    raise ConfigError("line %d: duplicate section %s" % (number, name))
                seen_default = True
                current = default
            else:
                if name in sections:
                    raise ConfigError("line %d: duplicate section %s" % (number, name))
                current = sections[name] = {}
            last_key = None
            continue
        if current is None:
            raise ConfigError("line %d: key outside a section" % number)
        key, sep, value = stripped.partition("=")
        key = key.strip().lower()
        if not sep or not key:
            raise ConfigError("line %d: expected key = value" % number)
        if key in current:
            raise ConfigError("line %d: duplicate key %s" % (number, key))
        current[key] = value.strip()
        last_key = key
    return default, sections
