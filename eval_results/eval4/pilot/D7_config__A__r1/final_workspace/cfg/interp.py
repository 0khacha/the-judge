"""Reference expansion: ${key}, ${section.key}, $$."""
import re

from .errors import ConfigError

TOKEN_RE = re.compile(r"\$\$|\$\{([^}]*)\}")


def _env_value(config, body):
    """Body of ${env:NAME} or ${env:NAME:-fallback}, without the 'env:' part."""
    name, sep, fallback = body.partition(":-")
    name = name.strip()
    value = config.env_var(name)
    if value is not None:
        return value
    if sep:
        return fallback
    raise ConfigError("unknown environment variable %s" % name)


def expand(config, section, key, text, stack):
    """Expand all references in `text`, the raw value of [section] key."""

    def repl(match):
        name = match.group(1)
        if name is None:
            return "$"
        name = name.strip()
        if name.startswith("env:"):
            return _env_value(config, name[len("env:"):])
        if "." in name:
            target_section, _, target_key = name.partition(".")
        else:
            target_section, target_key = section, name
        target_key = target_key.lower()
        if not config.has_section(target_section):
            raise ConfigError("unknown reference ${%s} in [%s] %s" % (name, section, key))
        try:
            return config.resolve(target_section, target_key, stack)
        except KeyError:
            raise ConfigError("unknown reference ${%s} in [%s] %s" % (name, section, key))

    return TOKEN_RE.sub(repl, text)
