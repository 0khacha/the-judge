# The Judge: Claude Code plugin

An independent verifier for the code Claude writes. Claude writes the tests first and
freezes them, then implements. At the end of every turn that changed code, a Stop hook
runs `judge verify`. Unless the verdict is PASS, the turn goes back to Claude with the
judge's numbered next actions: the failing assertion, the spec rule no test covers, the
planted bug no test caught.

## Install

```bash
pip install the-judge-verify
```

```text
/plugin install the-judge --marketplace 0khacha/the-judge
```

## What it adds

- **Stop hook**: active only in projects with a `.judge/` folder (`judge freeze` creates
  it), and only when code changed since the last check. It stops when the judge reports
  the loop as stuck. `THE_JUDGE_HOOK=always|off` overrides this.
- **Skill `judge-loop`**: the test-first protocol Claude follows.
- **Commands**: `/the-judge:freeze`, `/the-judge:verify`, `/the-judge:improve`.

Details: [the plugin guide](https://github.com/0khacha/the-judge/blob/main/docs/claude-code-plugin.md).
