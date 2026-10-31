# Evaluations

Pre-registered evaluations of the-judge-verify with Claude Haiku as the coding agent.
Each report states its protocol, its raw data and its verdict. The headline: the judge has
not been shown to make an agent's code more correct, because the agent without it
already passed the hidden tests. As a gate, 1.0.1 gave PASS to 10 of 12 wrong solutions
(evaluation 2); 1.0.2 gave PASS to none in 45 checks (evaluations 3-4).

| # | Question | Version | Report | Protocol | Raw data |
|---|---|---|---|---|---|
| 1 | Does the judge loop turn a one-shot builder into a continuous improver? | 1.0.0 | [eval1/REPORT.md](eval1/REPORT.md) | in the report | [eval1/](eval1/) |
| 2 | Does 1.0.1 make an agent's code more correct? | 1.0.1 | [REPORT2.md](REPORT2.md) | [PROTOCOL.md](PROTOCOL.md) | [eval2/](eval2/) |
| 3 | Same, on harder tasks (stopped at the pilot: no headroom) | 1.0.2 | [REPORT3.md](REPORT3.md) | [PROTOCOL3.md](PROTOCOL3.md) | [eval3/](eval3/) |
| 4 | Change requests in existing codebases (stopped at the pilot) | 1.0.2 | [REPORT4.md](REPORT4.md) | [PROTOCOL4.md](PROTOCOL4.md) | [eval4/](eval4/) |

Release build records: [RELEASE_1.0.1.md](RELEASE_1.0.1.md), [RELEASE_1.0.2.md](RELEASE_1.0.2.md) (built, not published), [RELEASE_1.1.0.md](RELEASE_1.1.0.md) (published).
Each `PROTOCOL*.sha256` holds the protocol's hash, recorded before any task existed.
