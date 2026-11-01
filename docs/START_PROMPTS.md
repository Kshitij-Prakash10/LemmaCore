# Start prompts (paste one into each laptop's Claude)

Before pasting: the repository must be cloned on that laptop, and you must have opened Claude Code in the repository folder. `CLAUDE.md` in the root loads automatically and sends the agent to the other documents.

## Laptop 1: Agent A (core)

```text
You are Agent A on team LemmaCore at Node Quest 2026 (a railway hackathon). Read CLAUDE.md, CONTEXT.md, OWNERSHIP.md, CONTRACT.md and AGENT_A.md in that order, completely. They contain the competition rules, the rubric, the problem, the solution, who owns which files, and the interfaces. Then do milestone M0 in AGENT_A.md right now: create your branch agent-a/core, install requirements-core.txt in a virtual environment, write failover/core/types.py and thin simulate() and advise() functions that match CONTRACT.md, add the contract test, merge to main, and update docs/STATUS_A.md. Work only in the files you own. A second agent (Agent B) is working in parallel on another laptop and cannot hear you: use docs/STATUS_A.md and docs/requests/ to communicate, and run git pull --rebase origin main every 15 minutes. Time is short: read docs/DEADLINE.md, run date, and compress the milestone schedule to the real deadline. Tell me when M0 is merged, then continue to M1 without waiting.
```

## Laptop 2: Agent B (data, ML, app)

```text
You are Agent B on team LemmaCore at Node Quest 2026 (a railway hackathon). Read CLAUDE.md, CONTEXT.md, OWNERSHIP.md, CONTRACT.md and AGENT_B.md in that order, completely. They contain the competition rules, the rubric, the problem, the solution, who owns which files, and the interfaces. Then do milestone M0 in AGENT_B.md right now: create your branch agent-b/ml-app, install requirements-ml.txt in a virtual environment and check that scikit-learn and Flask import on this Python version, download the MetroPT-3 dataset while the internet is available and log it in data/README.md, write failover/stubs/stub_core.py to match CONTRACT.md, build the app skeleton on the stub, merge to main, and update docs/STATUS_B.md. Work only in the files you own. A second agent (Agent A) is working in parallel on another laptop and cannot hear you: use docs/STATUS_B.md and docs/requests/ to communicate, and run git pull --rebase origin main every 15 minutes. Time is short: read docs/DEADLINE.md, run date, and compress the milestone schedule to the real deadline. Tell me when M0 is merged, then continue to M1 without waiting.
```

## When the human checks in

- At each checkpoint in `OWNERSHIP.md` ask each agent: "Which milestone are you on, what is blocked, and did you pull and merge?"
- If an agent reports a conflict or a missing field, read `docs/requests/` and decide.
- Never let either agent edit the other's files.
