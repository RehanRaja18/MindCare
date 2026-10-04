# Deployment — Render

How to run the MindCare API (`src/api/main.py`) on [Render](https://render.com)'s free tier, and keep it
awake for a demo. Deployment config only: nothing here changes the model or its features.

**Where things are.** This project lives in the `MindCare AI/` folder of the MindCare monorepo. Paths
in this document are relative to that folder, except the two files Render and GitHub require at the
**repository root**, marked "(repo root)" below.

**Files involved**

| File | What it does |
|---|---|
| `render.yaml` (repo root) | Render Blueprint: one Python web service with `rootDir: "MindCare AI"`, its build and start commands, and the Python version |
| `scripts/build_model_artifacts.sh` | Rebuilds every model artifact during the Render build (the 7 steps of `docs/setup.md`) |
| `.github/workflows/keep-alive.yml` (repo root) | Calls `/health` every 10 minutes so the free instance doesn't fall asleep |

## How the build works

The trained artifacts (`data/processed/*.pkl`, `*.npz`) are gitignored, so Render's fresh clone has
none of them. The build regenerates them from the raw CSV with exactly the scripts and order in
`docs/setup.md`:

```
pip install -r requirements.txt && bash scripts/build_model_artifacts.sh
```

- **Everything the build needs is in git:** `data/raw/mindcare_dataset_final.csv`,
  `data/processed/mindcare_processed_splits.npz` (the one tracked split, which no script can recreate),
  `reports/tuning_results_3class.json` and `reports/tuning_results_12feature.json`. Nothing is
  downloaded from elsewhere.
- **The build fails loudly.** Each step checks its own output against documented numbers and exits
  non-zero on a mismatch. A failed build never replaces the running deploy: Render keeps serving the
  previous one.
- **All 7 steps run,** although the API only needs steps 2, 5 and 7. Steps 3, 4 and 6 add about
  half a minute and keep the build identical to `docs/setup.md`.

The service then starts with:

```
uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
```

Render sets `$PORT` itself.

## Environment variables

| Variable | Where | Value | Commit it? |
|---|---|---|---|
| `PYTHON_VERSION` | `render.yaml` | `3.13.13` | Yes, already committed. It matches the project's interpreter and the pinned `scikit-learn==1.9.1` / `xgboost==3.4.1` |
| `PORT` | Set by Render | — | No. Never set it yourself |
| `RENDER_SERVICE_URL` | **GitHub** repository variable (not Render) | Your service URL, e.g. `https://mindcare-api.onrender.com` | No. Set it by hand after the first deploy (see "Keep-alive") |

**Nothing needs to be set in the Render dashboard.** The app reads no environment variables. The
model file paths and the review threshold (`HIGH_PROBA_THRESHOLD = 0.025`) are deliberately constants
in `src/api/main.py`, pinned by `tests/test_api.py`. They are not exposed as environment variables,
because a typo in a dashboard field would silently change which patients get flagged for review.
Changing them is a code change, with tests and a decision-log entry in `CLAUDE.md`.

## One-time setup on Render

1. **Sign in to Render** and connect your GitHub account (Render asks for access to the
   repository; it's public, so read access is enough).
2. **Create the service from the Blueprint:** New → **Blueprint** → choose the
   `m-bilal-Ibrahim/MindCare` repository and the **`main`** branch. Render reads `render.yaml` from
   the repository root and shows one web service, `mindcare-api`, on the **Free** plan, with root
   directory `MindCare AI`, so the build and start commands run inside that folder.
3. **Apply.** The first build installs the requirements and runs the 7 build steps; expect several
   minutes. In the build log, every step prints `=== Step N/7 done`, and the last line is
   `=== All 7 steps passed; the API's artifacts are in place.`
4. **Check it.** When the deploy shows **Live**, open:
   - `https://<your-service>.onrender.com/health` — should return `{"status":"ok",...}`
   - `https://<your-service>.onrender.com/docs` — the interactive API docs
   - `https://<your-service>.onrender.com/form` — the manual test form
5. **Copy the service URL** (shown at the top of the service page) for the keep-alive setup below.

**The deployed API is public.** Anyone with the URL can call `/predict` and open `/form`. There is no
authentication. That's fine for a demo on very likely synthetic data, but don't send real patient
data to it.

## Redeploying

- **Automatic:** with `autoDeploy: true`, every push to `main` that changes files under
  `MindCare AI/` triggers a new build and deploy. Changes elsewhere in the monorepo (Backend, App,
  Web) don't.
- **Manual:** on the service page, **Manual Deploy → Deploy latest commit**. Use **Clear build cache &
  deploy** if a dependency seems stale.
- **If a build fails:** open the build log and find the last `=== Step N/7` line. A
  `MISMATCH` or `STOP:` message means that step didn't reproduce its documented numbers. The
  previous deploy keeps running meanwhile.
- **To build from another branch,** change `branch:` in the root `render.yaml` and push.

## Keep-alive

Render's free web services **go to sleep after about 15 minutes without traffic**. The next request
then waits for a cold start, which can take a minute or more, which is bad in a live demo.
`.github/workflows/keep-alive.yml` (at the repository root) calls `/health` every 10 minutes to
prevent that.

**The workflow only runs from the default branch.** GitHub runs a workflow, on its schedule **or**
from the manual **Run workflow** button, only if the workflow file is on the repository's default
branch (`main`). On any other branch, neither works.

**After the first deploy, set the URL** (it doesn't exist until Render assigns it):

1. On GitHub: repository **Settings → Secrets and variables → Actions → Variables** tab →
   **New repository variable**.
2. Name `RENDER_SERVICE_URL`, value your service URL, e.g. `https://mindcare-api.onrender.com`
   (no trailing `/health`). A variable, not a secret, is right here: the URL is public anyway, and
   it shows up readably in the run logs.
3. Test it, once the workflow is on the default branch: **Actions → Keep Render service awake →
   Run workflow**. The run should go green and log `Healthy on attempt 1: {"status":"ok",...}`.
   After that, the 10-minute schedule runs on its own.

**It fails loudly.** A run fails (red, and GitHub emails you about failed scheduled runs) if:
- `RENDER_SERVICE_URL` isn't set;
- `/health` doesn't return HTTP 200 within three attempts, 20 seconds apart, each allowed 90 seconds;
- `/health` returns 200 but without `"status":"ok"`, meaning the model didn't load.

### This is a workaround, not a guarantee

- **GitHub may run schedules late or skip them** when its runners are busy, so gaps longer than 15
  minutes can still happen and the service can still fall asleep.
- **GitHub disables scheduled workflows** in a public repository after 60 days without activity. Re-enable
  it from the Actions tab if that happens.
- **Render's free tier has a monthly limit** of 750 free instance hours per workspace. Keeping one
  service awake all month uses about 720–744 of them, so a second free service in the same workspace
  would run out.

**For the defense/viva day, don't rely on the keep-alive alone.** Either:
- open `https://<your-service>.onrender.com/health` yourself 5–10 minutes before you present, and
  again just before the demo, until it answers instantly; or
- for zero risk, temporarily upgrade the service to a paid instance type for that day (it doesn't
  sleep), and switch back afterwards.

## What has been verified, and what hasn't

Verified on 2026-10-04 in a clean copy of the repository (tracked files only, so no model
artifacts) with a new Python 3.13.13 virtual environment installed from `requirements.txt`:

- **The build command works:** all 7 steps passed and every step's own check matched (27 seconds
  locally).
- **The start command works:** `uvicorn src.api.main:app` from the clean copy served `/health` with
  `"status":"ok"`, plus `/form` and `/docs`. The project's own model file was hidden during startup,
  to prove the server loaded the freshly built one. `/predict` returned the documented worked example
  in `docs/api_usage.md` to every digit.
- **The keep-alive script works:** run locally against a healthy server, a stopped server, a server
  answering 200 with `"status":"not_ready"`, and with the URL unset. Only the healthy case passed;
  the other three failed with an error.

**Not verified locally:**
- **Render's Linux build machine.** No Linux environment was available, so a difference between
  the Windows and Linux builds of the same package versions can't be ruled out. If one exists, a
  step's check fails and the build stops, rather than serving a different model.
- **Unpinned packages.** Only `scikit-learn` and `xgboost` are pinned in `requirements.txt`. Others
  (pandas, numpy, fastapi, uvicorn, ...) install at whatever version is newest when Render builds.
  This matters: with scikit-learn 1.8.0 instead of the pinned 1.9.1, step 4's check fails. If a
  future Render build fails a check after an upstream release, pin the affected package to the
  version in the project's working environment.
- **The GitHub Actions run itself** (the script was run locally, not on GitHub's runners). Both the
  scheduled and the manual trigger need the workflow on the default branch first.

## Verify locally

The build and start commands can be run on any machine before relying on Render. Run these from
inside `MindCare AI/`, as Render does:

```bash
python -m venv .venv_deploy_check
.venv_deploy_check/Scripts/python -m pip install -r requirements.txt
PATH="$PWD/.venv_deploy_check/Scripts:$PATH" bash scripts/build_model_artifacts.sh
.venv_deploy_check/Scripts/uvicorn src.api.main:app --host 127.0.0.1 --port 8010
```

Then open `http://127.0.0.1:8010/health`. On macOS/Linux use `.venv_deploy_check/bin`.
