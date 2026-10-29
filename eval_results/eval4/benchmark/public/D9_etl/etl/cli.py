"""Command line: run FILE --fields id:int,name:str [--key id] [--out csv|jsonl]"""
from . import writer
from .pipeline import EtlError, run
from .schema import parse_spec

USAGE = "usage: etl run FILE --fields SPEC [--key FIELD] [--out csv|jsonl]"


def _read_file(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _options(args):
    opts, i = {}, 0
    while i < len(args):
        if args[i].startswith("--") and i + 1 < len(args):
            opts[args[i]] = args[i + 1]
            i += 2
        else:
            raise ValueError("bad argument %r" % args[i])
    return opts


def main(argv, out=print, read=_read_file):
    if len(argv) < 2 or argv[0] != "run":
        out(USAGE)
        return 2
    try:
        opts = _options(argv[2:])
        if "--fields" not in opts:
            out(USAGE)
            return 2
        schema = parse_spec(opts["--fields"])
        result = run(read(argv[1]), schema, key=opts.get("--key"))
    except (OSError, ValueError, EtlError) as exc:
        out("error: %s" % exc)
        return 1
    st = result.stats
    out("read=%d accepted=%d rejected=%d duplicates=%d" % (st["read"], st["accepted"], st["rejected"], st["duplicates"]))
    fmt = opts.get("--out", "csv")
    text = writer.to_jsonl(result, schema) if fmt == "jsonl" else writer.to_csv(result, schema)
    for line in text.splitlines():
        out(line)
    for reject in result.rejects:
        out("! %s" % reject.reason)
    return 0
