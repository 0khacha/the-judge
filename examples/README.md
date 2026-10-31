# Examples

| Example | Shows | Time |
|---|---|---|
| [simple_cache](simple_cache/README.md) | The full loop: spec rules, tests frozen first, a buggy implementation (FAIL), the fix (PASS with mutation testing), and `judge improve --agent`. **Start here.** | 2 min |
| [agent_loop](agent_loop/run_agent_loop.py) | `improve(repair_func=...)`: your own repair step acting on `next_actions`, FAIL to PASS in two rounds. Runs offline. | 30 s |
| [visual_portfolio](visual_portfolio/README.md) | A web page: HTML checked by tests (finds six dead links), and a screenshot review with `judge improve`. | 2 min |

Work on a copy (`cp -r examples/<name> /tmp/<name>`) so the examples stay unchanged:
`judge freeze` and `judge verify` write a `.judge/` folder into the project.
