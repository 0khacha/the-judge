import os, json
from _h import *
T = "D9_etl"
r = mk(T, "reference")
p = lambda *a: os.path.join(r, *a)
P = p("etl/pipeline.py")
rep(P, "def run(text, schema, key=None):\n    header, raw_rows = read_rows(text)", '''def _key_names(key):
    if key is None:
        return []
    if isinstance(key, str):
        return [key]
    return list(key)


def run(text, schema, key=None, keep="first"):
    if keep not in ("first", "last"):
        raise EtlError("keep must be 'first' or 'last'")
    names = _key_names(key)
    header, raw_rows = read_rows(text)''')
rep(P, '''    if key is not None:
        if key not in schema.names:
            raise EtlError("unknown key field %s" % key)
        if not schema.field(key).required:
            raise EtlError("key field %s must be required" % key)
''', '''    for name in names:
        if name not in schema.names:
            raise EtlError("unknown key field %s" % name)
        if not schema.field(name).required:
            raise EtlError("key field %s must be required" % name)
''')
rep(P, '''    duplicates = 0
    if key is not None:
        seen, kept = {}, []
        for line, row in good:
            value = row[key]
            if value in seen:
                duplicates += 1
                rejects.append(Reject(line, "line %d: duplicate of line %d" % (line, seen[value])))
                continue
            seen[value] = line
            kept.append((line, row))
        good = sorted(kept, key=lambda item: item[1][key])
''', '''    duplicates = superseded = 0
    if names:
        seen, kept = {}, []                      # seen: key tuple -> index in kept
        for line, row in good:
            value = tuple(row[n] for n in names)
            if value in seen:
                duplicates += 1
                slot = seen[value]
                if keep == "first":
                    rejects.append(Reject(line, "line %d: duplicate of line %d" % (line, kept[slot][0])))
                    continue
                old_line = kept[slot][0]
                superseded += 1
                rejects.append(Reject(old_line, "line %d: superseded by line %d" % (old_line, line)))
                kept[slot] = (line, row)
                continue
            seen[value] = len(kept)
            kept.append((line, row))
        good = sorted(kept, key=lambda item: tuple(item[1][n] for n in names))
''')
rep(P, '"rejected": len(rejects), "duplicates": duplicates}', '"rejected": len(rejects), "duplicates": duplicates,\n             "superseded": superseded}')
C = p("etl/cli.py")
rep(C, "[--key FIELD] [--out csv|jsonl]\"", "[--key FIELD[,FIELD...]] [--keep first|last] [--out csv|jsonl]\"")
rep(C, '''        result = run(read(argv[1]), schema, key=opts.get("--key"))''', '''        key = [k.strip() for k in opts["--key"].split(",") if k.strip()] if "--key" in opts else None
        result = run(read(argv[1]), schema, key=key, keep=opts.get("--keep", "first"))''')
rep(C, '''    out("read=%d accepted=%d rejected=%d duplicates=%d" % (st["read"], st["accepted"], st["rejected"], st["duplicates"]))''',
       '''    out("read=%d accepted=%d rejected=%d duplicates=%d superseded=%d" % (
        st["read"], st["accepted"], st["rejected"], st["duplicates"], st["superseded"]))''')
w = clone(T, "reference", "wrong_1")   # stats and CLI not updated
rep(os.path.join(w, "etl/pipeline.py"), '"rejected": len(rejects), "duplicates": duplicates,\n             "superseded": superseded}', '"rejected": len(rejects), "duplicates": duplicates}')
C1 = os.path.join(w, "etl/cli.py")
rep(C1, '''        key = [k.strip() for k in opts["--key"].split(",") if k.strip()] if "--key" in opts else None
        result = run(read(argv[1]), schema, key=key, keep=opts.get("--keep", "first"))''', '''        result = run(read(argv[1]), schema, key=opts.get("--key"))''')
rep(C1, '''    out("read=%d accepted=%d rejected=%d duplicates=%d superseded=%d" % (
        st["read"], st["accepted"], st["rejected"], st["duplicates"], st["superseded"]))''', '''    out("read=%d accepted=%d rejected=%d duplicates=%d" % (st["read"], st["accepted"], st["rejected"], st["duplicates"]))''')
w = clone(T, "reference", "wrong_2")   # rejects no longer sorted by line
rep(os.path.join(w, "etl/pipeline.py"), "    rejects.sort(key=lambda r: r.line)\n", "")
json.dump({"task": T, "lines": 0, "change_requirements": 6, "traps": [
 "keep=last: reject names the next row with the same key (chain), attached to superseded line",
 "invalid rows must not claim keys / supersede",
 "duplicates after coercion (01 == 1)",
 "stats: superseded added, duplicates counts both, rejected includes all",
 "cli --key comma list, --keep, summary format",
 "rejects must stay sorted by line (regression)",
 "sorted by key tuple with numeric comparison"]}, open(os.path.join(H, T, "label.json"), "w"), indent=1)
