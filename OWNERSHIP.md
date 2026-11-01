# Ownership and git rules

The two agents work in parallel with no direct line to each other. Disjoint file ownership is what prevents overlap.

## Who owns what

| Path | Owner | Notes |
|---|---|---|
| `failover/core/**` | **Agent A** | Plant models, advisor, harness, report |
| `config/**` | **Agent A** | `loco.json`. Others read it, never edit it |
| `CONTRACT.md` | **Agent A** | Changes only through `docs/requests/` |
| `tests/core/**` | **Agent A** | |
| `demo_outputs/**` | **Agent A** | Committed copies of harness outputs so Agent B never waits |
| `docs/model.md`, `docs/STATUS_A.md` | **Agent A** | |
| `failover/ml/**` | **Agent B** | Data loading, training, inference |
| `failover/app/**` | **Agent B** | Flask server and static pages (no CDN) |
| `failover/stubs/**` | **Agent B** | Temporary stand-in for the core until it lands |
| `data/**`, `models/**` | **Agent B** | `data/raw` is not committed |
| `tests/ml/**`, `tests/app/**` | **Agent B** | |
| `docs/ml.md`, `docs/STATUS_B.md` | **Agent B** | |
| `README.md`, `CONTEXT.md`, `OWNERSHIP.md`, `CLAUDE.md`, `AGENT_A.md`, `AGENT_B.md`, `Makefile`, `requirements*.txt`, `.gitignore`, `docs/AI_DISCLOSURE.md`, `docs/START_PROMPTS.md`, `docs/DEMO.md`, `docs/PITCH.md` | **Humans** | Agents do not edit these. Ask through `docs/requests/` |
| `failover/__init__.py`, `failover/*/__init__.py` | **Humans** | Created in the skeleton |
| `docs/requests/**` | **Anyone** | Create new files only. Never edit an existing file |

Requirements: Agent A adds packages to `requirements-core.txt`. Agent B adds packages to `requirements-ml.txt`. The root `requirements.txt` includes both and is human-owned. This keeps installs from conflicting.

## The request protocol

If you need a change in something you do not own (for example a new field in `CONTRACT.md`), create a new file `docs/requests/<YYYYMMDD-HHMM>-<agent>-<short-title>.md` with: what you need, why, and what you will do meanwhile. The owner answers by creating a new file named `...-reply.md`. New files never conflict.

## Branches

- `main` is the integration branch. It must always import and pass the tests of both areas.
- Agent A works on `agent-a/core`. Agent B works on `agent-b/ml-app`. Create them from `main`.
- Merge to `main` yourself when your tests pass:

```bash
git checkout main && git pull --rebase origin main
git merge --no-ff <your-branch>
# run your own tests, then the whole suite: pytest -q
git push origin main
git checkout <your-branch> && git rebase main
```

Because ownership is disjoint, merges should not conflict. If one does, stop, do not resolve it by editing the other agent's file, and write a request file.

## Rhythm

- Every 15 minutes: `git pull --rebase origin main`, read `docs/STATUS_A.md` and `docs/STATUS_B.md`, and read any new files in `docs/requests/`.
- After each milestone: update your status file, commit, push your branch, merge to `main`.
- Commit small and often. Message format: `core: ...`, `ml: ...`, `app: ...`, `docs: ...`.

## Integration checkpoints

| Checkpoint | When (from start) | What must work |
|---|---|---|
| **I0** | 10 min | Skeleton installed on both laptops. Agent A has merged `types` and a stub `simulate`/`advise` per `CONTRACT.md`. Agent B has the app skeleton on the stub. |
| **I1** | 35 min | Agent B switches from `stubs` to the real core. One end-to-end hard case runs: scenario in, advice out, shown on the screen. This is the progress-review slice. |
| **I2** | 70 min | The harness has produced `coverage.json`. The app shows the coverage map. The classifier is trained on core-generated data and wired to "Auto-diagnose". |
| **I3** | 95 min | Report export, assumptions screen, sliders. Real-data slide ready. |
| **Freeze** | last 15 min | No new features. README, tests, offline check with Wi-Fi off, disclosure. |

## The human's job

Create the GitHub repository and push the skeleton. Start both agents with the prompts in `docs/START_PROMPTS.md`. Watch the clock and call each checkpoint. Run `make demo` at I2 and at the freeze. Ask the mentor the five questions and update `config/loco.json` through Agent A. Write the pitch and rehearse.
