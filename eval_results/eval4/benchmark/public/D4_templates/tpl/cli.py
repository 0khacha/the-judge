"""python -m tpl.cli TEMPLATE_FILE DATA_JSON [--strict]"""
import json
import sys

from . import TemplateError, render


def main(argv=None, out=print):
    argv = list(sys.argv[1:] if argv is None else argv)
    strict = "--strict" in argv
    args = [a for a in argv if a != "--strict"]
    if len(args) != 2:
        out("usage: tpl TEMPLATE DATA.json [--strict]")
        return 2
    try:
        with open(args[0], encoding="utf-8") as fh:
            source = fh.read()
        with open(args[1], encoding="utf-8") as fh:
            data = json.load(fh)
        out(render(source, data, strict=strict))
    except (OSError, ValueError, TemplateError) as exc:
        out("error: %s" % exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
