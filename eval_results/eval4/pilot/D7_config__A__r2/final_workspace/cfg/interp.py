"""Reference expansion: ${key}, ${section.key}, ${env:NAME[:-fallback]}, $$."""
import re

from .errors import ConfigError

# group 1 and 2: env name and fallback of ${env:NAME:-fallback}; group 3: ${ref}
TOKEN_RE = re.compile(r"\$\$|\$\{env:([^}:]*)(?::-([^}]*))?\}|\$\{([^}]*)\}")


def expand(config, section, key, text, stack):
    """Expand all references in `text`, the raw value of [section] key.

    Substituted environment values are inserted literally: the substitution
    is a single pass, so their content is never expanded again.
    """

    def repl(match):
        if match.group(3) is None and match.group(1) is None:
            return "$"
        if match.group(3) is None:
            name = match.group(1)
            if name in config._environ:
                return config._environ[name]
            if match.group(2) is not None:
                return match.group(2)
            raise ConfigError("unknown environment variable %s" % name)

        name = match.group(3).strip()
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
