"""Append one agent run's usage to eval_results/eval3/agent_usage.jsonl.

usage: python log3.py "<id>|<tokens>|<tool_uses>|<duration_ms>|<report summary>"
"""
import json
import sys

OUT = "C:/projects/the-judge/eval_results/eval3/agent_usage.jsonl"
rid, tokens, tools, ms, report = sys.argv[1].split("|", 4)
with open(OUT, "a", encoding="utf-8") as f:
    f.write(json.dumps({"id": rid, "tokens": int(tokens), "tool_uses": int(tools),
                        "duration_ms": int(ms), "report": report}) + "\n")
print(sum(1 for _ in open(OUT, encoding="utf-8")), "logged")
