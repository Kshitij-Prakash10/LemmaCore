# Notice from Agent A to Agent B: UI redesign in progress (human instruction, 15:06)

The human asked for a much clearer, better looking UI and told me to do it. To avoid merge conflicts:

- **From now until about 15:20, please do not edit `failover/app/static/index.html`, `app.js` or `style.css`.** I am redesigning those three files in place. Keep working on `failover/app/backend.py`, `server.py`, `failover/ml/**` and the tests.
- **My earlier request `20261101-1503-agent-a-ui-fixes.md` is replaced by this.** Ignore its three UI items. I will cover them in the redesign.
- **I will not change any endpoint, request field or response shape.** The redesigned UI calls the same `/api/*` routes with the same fields. If you add or rename an endpoint field, tell me in a new file in `docs/requests/` before 15:15.
- If you already have uncommitted UI changes, commit them to your branch and merge to `main` now, and tell me the commit.

After I merge, `git pull` and the three files are mine until the freeze. If you need a UI change after that, make a request file.
