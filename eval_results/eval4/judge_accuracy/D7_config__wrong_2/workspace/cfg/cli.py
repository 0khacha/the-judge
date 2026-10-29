"""python -m cfg.cli show FILE | get FILE section.key | source FILE section.key"""
import os
import sys

from .errors import ConfigError
from .loader import Config


def _load(path, prefix):
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


def main(argv=None, out=print):
    argv = list(sys.argv[1:] if argv is None else argv)
    argv, prefix = _split_prefix(argv)
    if len(argv) < 2 or argv[0] not in ("show", "get", "source"):
        out("usage: cfg show FILE | cfg get FILE section.key | cfg source FILE section.key")
        return 2
    try:
        config = _load(argv[1], prefix)
        if argv[0] == "show":
            for section, values in config.as_dict().items():
                out("[%s]" % section)
                for key, value in values.items():
                    out("%s = %s" % (key, value.replace("\n", "\\n")))
        else:
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
            out(value)
    except (OSError, ConfigError, KeyError) as exc:
        out("error: %s" % (exc.args[0] if exc.args else exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
