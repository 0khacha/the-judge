"""python -m cfg.cli show FILE | get FILE section.key | source FILE section.key

Environment overrides come from os.environ (read when the command runs);
--prefix P (or --prefix=P) may appear anywhere after the command name.
"""
import os
import sys

from .errors import ConfigError
from .loader import Config

USAGE = "usage: cfg show FILE | cfg get FILE section.key | cfg source FILE section.key"
COMMANDS = ("show", "get", "source")
DEFAULT_PREFIX = "APP"


def _take_prefix(args):
    """Strip --prefix options from args. Returns (rest, prefix), rest None if malformed."""
    rest = []
    prefix = DEFAULT_PREFIX
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--prefix":
            if i + 1 >= len(args):
                return None, None
            prefix = args[i + 1]
            i += 2
            continue
        if arg.startswith("--prefix="):
            prefix = arg[len("--prefix="):]
        else:
            rest.append(arg)
        i += 1
    return rest, prefix


def _load(path, prefix):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    return Config.loads(text, env=dict(os.environ), prefix=prefix)


def main(argv=None, out=print):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in COMMANDS:
        out(USAGE)
        return 2
    command = argv[0]
    args, prefix = _take_prefix(argv[1:])
    if args is None:
        out(USAGE)
        return 2

    if command == "show":
        if not args:
            out(USAGE)
            return 2
        path = args[0]
    else:
        if len(args) != 2 or "." not in args[1]:
            out("usage: cfg %s FILE section.key" % command)
            return 2
        path, target = args
        section, _, key = target.partition(".")

    try:
        config = _load(path, prefix)
        if command == "show":
            for section, values in config.as_dict().items():
                out("[%s]" % section)
                for key, value in values.items():
                    out("%s = %s" % (key, value.replace("\n", "\\n")))
        elif command == "get":
            value = config.get(section, key, None)
            if value is None:
                out("error: no such key %s" % target)
                return 1
            out(value)
        else:
            try:
                origin = config.source(section, key)
            except KeyError:
                out("error: no such key %s" % target)
                return 1
            out(origin)
    except (OSError, ConfigError, KeyError) as exc:
        out("error: %s" % (exc.args[0] if exc.args else exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
