"""python -m cfg.cli show FILE | get FILE section.key | source FILE section.key

Each command accepts --prefix P (default APP) anywhere after the command name.
"""
import os
import sys

from .errors import ConfigError
from .loader import Config

USAGE = "usage: cfg show FILE | cfg get FILE section.key | cfg source FILE section.key"


def _load(path, prefix):
    with open(path, encoding="utf-8") as fh:
        return Config.loads(fh.read(), env=os.environ, prefix=prefix)


def _split_prefix(args):
    """Remove --prefix P from args. Returns (prefix, remaining) or None if P is missing."""
    prefix = "APP"
    rest = []
    i = 0
    while i < len(args):
        if args[i] == "--prefix":
            if i + 1 >= len(args):
                return None
            prefix = args[i + 1]
            i += 2
        else:
            rest.append(args[i])
            i += 1
    return prefix, rest


def main(argv=None, out=print):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("show", "get", "source"):
        out(USAGE)
        return 2
    command = argv[0]

    split = _split_prefix(argv[1:])
    if split is None:
        out(USAGE)
        return 2
    prefix, args = split

    if command == "show":
        if not args:
            out("usage: cfg show FILE")
            return 2
    elif len(args) != 2 or "." not in args[1]:
        out("usage: cfg %s FILE section.key" % command)
        return 2

    try:
        config = _load(args[0], prefix)
        if command == "show":
            for section, values in config.as_dict().items():
                out("[%s]" % section)
                for key, value in values.items():
                    out("%s = %s" % (key, value.replace("\n", "\\n")))
        elif command == "get":
            section, _, key = args[1].partition(".")
            value = config.get(section, key, None)
            if value is None:
                out("error: no such key %s" % args[1])
                return 1
            out(value)
        else:
            section, _, key = args[1].partition(".")
            try:
                origin = config.source(section, key)
            except KeyError:
                out("error: no such key %s" % args[1])
                return 1
            out(origin)
    except (OSError, ConfigError, KeyError) as exc:
        out("error: %s" % (exc.args[0] if exc.args else exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
