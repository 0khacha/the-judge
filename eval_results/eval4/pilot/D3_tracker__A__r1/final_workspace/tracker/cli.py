"""Command line front end: main(argv, store, out=print) -> exit code."""
from datetime import date

from . import views
from .store import BlockedError

USAGE = "commands: add, done, reopen, rm, list, ready, agenda, summary"


def parse_options(args, multi=("--tag", "--dep")):
    """Split args into (positionals, options). Options in `multi` can repeat."""
    positional, options = [], {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            if i + 1 >= len(args):
                raise ValueError("option %s needs a value" % arg)
            value = args[i + 1]
            if arg in multi:
                options.setdefault(arg, []).append(value)
            else:
                options[arg] = value
            i += 2
        else:
            positional.append(arg)
            i += 1
    return positional, options


def _add(store, args, out):
    pos, opt = parse_options(args)
    if len(pos) != 1:
        raise ValueError("usage: add TITLE [--due YYYY-MM-DD] [--prio N] [--tag T] [--dep ID] [--repeat KIND]")
    due = date.fromisoformat(opt["--due"]) if "--due" in opt else None
    task = store.add(pos[0], due=due, priority=int(opt.get("--prio", 2)),
                     tags=opt.get("--tag", []), deps=[int(d) for d in opt.get("--dep", [])],
                     repeat=opt.get("--repeat"))
    out("added #%d" % task.id)


def _done(store, args, out):
    task = store.complete(int(args[0]))
    out("done #%d" % task.id)
    if task.next_id is not None:
        successor = store.get(task.next_id)
        out("next #%d due %s" % (successor.id, successor.due.isoformat()))


def _reopen(store, args, out):
    out("reopened #%d" % store.reopen(int(args[0])).id)


def _rm(store, args, out):
    store.delete(int(args[0]))
    out("removed #%s" % args[0])


def _fmt(task):
    text = "#%d [%s] P%d %s due %s" % (
        task.id, task.status, task.priority, task.title, task.due.isoformat() if task.due else "-")
    if task.repeat is not None:
        text += " repeat %s" % task.repeat
    return text


def _list(store, args, out):
    pos, opt = parse_options(args)
    for task in store.tasks(status=opt.get("--status"), tag=opt.get("--tag", [None])[0]):
        out(_fmt(task))


def _ready(store, args, out):
    for task in store.ready():
        out(_fmt(task))


def _agenda(store, args, out):
    pos, opt = parse_options(args)
    out(views.agenda(store, int(opt.get("--days", 7))))


def _summary(store, args, out):
    out(views.summary(store))


COMMANDS = {"add": _add, "done": _done, "reopen": _reopen, "rm": _rm, "list": _list,
            "ready": _ready, "agenda": _agenda, "summary": _summary}


def main(argv, store, out=print):
    if not argv or argv[0] not in COMMANDS:
        out(USAGE)
        return 2
    try:
        COMMANDS[argv[0]](store, argv[1:], out)
    except (BlockedError, KeyError, ValueError, IndexError) as exc:
        out("error: %s" % (exc.args[0] if exc.args else exc))
        return 1
    return 0
