# Failover Guardian: Node Quest 2026 (team LemmaCore)

Two Claude Code agents work in this repository at the same time, from two laptops. They cannot talk to each other. The repository is the only channel.

Read these files in this order before you do anything else:

1. `CONTEXT.md` (the competition rules, the problem, the solution, the scope)
2. `OWNERSHIP.md` (who owns which path, and the git rules)
3. `CONTRACT.md` (the interfaces between the two agents)
4. Your own brief: `AGENT_A.md` or `AGENT_B.md`

Your role comes from the first message the user sends: "You are Agent A" or "You are Agent B". If the message does not say, ask once and wait.

## Hard rules

1. **Edit only paths your role owns** (see `OWNERSHIP.md`). If you need a change in a path you do not own, create a new file in `docs/requests/` (see the README there). Never edit the other agent's files.
2. **Git.** Work on your own branch. Run `git pull --rebase origin main` every 15 minutes and before every push. Never force-push. Never rewrite shared history. Merge to `main` only when the tests for your own area pass.
3. **Offline at run time.** Nothing may need the internet when the app runs: no CDN links, no cloud APIs, no model downloads at run time. Downloads are allowed only during setup, and the downloaded data must be stored locally.
4. **Honesty.** Every loco number is tagged `assumed` or `confirmed`. Do not invent data, citations or accuracy figures. Synthetic data is always labelled synthetic. Report metrics only from held-out evaluation.
5. **Scope.** Build what your brief says, in the milestone order. A working core beats a polished mock-up. Do not add features that are not in your brief.
6. **Status.** After each milestone, update your status file (`docs/STATUS_A.md` or `docs/STATUS_B.md`): what works, what is stubbed, what you need from the other agent, and any AI tools or open-source code you used. The competition requires us to disclose AI and open-source use.
7. **Determinism.** Every random process takes a seed. A stranger must be able to reproduce every number with one command.
8. **Time.** Read `docs/DEADLINE.md` first and compress the milestone schedule to the real deadline. Run `date` to see how much time is left. A progress review will check that the software runs and handles the hard case. Prefer a thin end-to-end slice early over a perfect module late.

## Style

Python 3, standard library plus the packages in the requirements files. Type hints on public functions. Short docstrings that say units. Tests with pytest. No emojis in code or docs.
