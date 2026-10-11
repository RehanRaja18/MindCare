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
| `scripts/deploy_artifacts.py` | Render's build check (`verify`): proves the committed served artifacts are the validated ones and serve the documented prediction |
| `data/processed/deploy_artifacts.json` | Manifest of the three committed served artifacts: hashes, library versions, expected example output |
| `scripts/build_model_artifacts.sh` | **Local development only:** rebuilds every model artifact (the 7 steps of `docs/setup.md`). Render does not run it |
| `.github/workflows/keep-alive.yml` (repo root) | Calls `/health` every 10 minutes so the free instance doesn't fall asleep |

## How the build works

**Render does not retrain the model.** The three files the API serves are committed to git, and the
build only checks them:

```
pip install -r requirements.txt && python scripts/deploy_artifacts.py verify
```

The check fails the build (non-zero exit) unless all of these hold:

1. **The committed files are the validated ones.** Each served file exists and matches the SHA-256
   recorded in `data/processed/deploy_artifacts.json`.
2. **The library versions match.** The installed `scikit-learn` and `xgboost` equal the versions
   that wrote the pickles (`1.9.1` and `3.4.1`, both pinned in `requirements.txt`).
3. **The app serves the documented example.** It starts the real app in-process (FastAPI's
   `TestClient`). `/health` must report `"ok"`. `/predict` must return the worked example from
   `docs/api_usage.md`: same class and labels, probabilities within 1e-6 of the manifest.
   `/patient-summary` must return 200 with its caveat.

A failed build never replaces the running deploy: Render keeps serving the previous one.

The service then starts with:

```
uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
```

Render sets `$PORT` itself.

## Why the served model is committed

**Most model artifacts are still kept out of git.** That policy is unchanged:
`data/processed/*.pkl` and `*.npz` are gitignored and regenerated with `docs/setup.md`. This is a
**deployment-only exception for exactly three files**, the ones the API loads:

| File | Size |
|---|---:|
| `data/processed/mindcare_label_encoder_3class.pkl` | 399 bytes |
| `data/processed/mindcare_preprocessor_11feature_v2.pkl` | 3.5 KB |
| `data/processed/mindcare_final_model_11feature_v2_xgb.pkl` | 1.0 MB |

Each has a `!` exception in `.gitignore`. Their manifest, `data/processed/deploy_artifacts.json`, is
committed beside them.

**Why:** the first deploy rebuilt every artifact on Render with the 7 regeneration scripts, and
failed at step 6 (`adopt_xgboost_12feature_model`). Steps 1–5 reproduced their documented numbers
exactly. The retrained XGBoost model did not: multi-threaded tree building on Render's Linux machine
gives slightly different floating-point results from the Windows machine the model was validated
on. That's not a data or logic bug, but it means **retraining XGBoost isn't bit-reproducible across
platforms**, so a deploy can't be guaranteed to serve the validated model by retraining it. Committing
the validated files guarantees it, and the build check proves it on every deploy.

**Local development still uses the regeneration scripts**, exactly as before:
`bash scripts/build_model_artifacts.sh` (docs/setup.md). Its last step runs the same check, so you
know at once whether your rebuilt served files still match the deployed ones.
- On the machine and library versions that built them (Windows, Python 3.13.13, scikit-learn 1.9.1,
  xgboost 3.4.1), regeneration reproduces them **byte for byte**; this was checked by SHA-256, so
  they don't show as modified.
- Anywhere else they may differ. That's fine for local work, but **don't commit them**; restore the
  committed versions with
  `git checkout -- data/processed/mindcare_label_encoder_3class.pkl data/processed/mindcare_preprocessor_11feature_v2.pkl data/processed/mindcare_final_model_11feature_v2_xgb.pkl`.

### Updating the deployed model

Only when deliberately adopting a new served model (a decision recorded in `CLAUDE.md`, like every
model change):

1. Rebuild and validate it locally (docs/setup.md); every step's own check must pass.
2. Run `python scripts/deploy_artifacts.py write` to record its hashes, library versions and the
   new expected example output in `data/processed/deploy_artifacts.json`.
3. Update the worked example in `docs/api_usage.md` if its numbers changed.
4. Commit the three files and the manifest **together**, then push. The Render build checks them
   against the new manifest.

## Environment variables

| Variable | Where | Value | Commit it? |
|---|---|---|---|
| `PYTHON_VERSION` | `render.yaml` | `3.13.13` | Yes, already committed. It matches the project's interpreter and the pinned `scikit-learn==1.9.1` / `xgboost==3.4.1` |
| `PORT` | Set by Render | — | No. Never set it yourself |
| `RENDER_SERVICE_URL` | **GitHub** repository variable (not Render) | Your service URL, e.g. `https://mindcare-api-fysd.onrender.com` | No. Set it by hand after the first deploy (see "Keep-alive") |

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
3. **Apply.** The first build installs the requirements and runs the artifact check; expect a few
   minutes. The build log should end with
   `=== Deployment artifacts verified: the committed model loads and serves the documented prediction.`
   (An existing service redeploys automatically when this reaches `main`.)
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
- **If a build fails:** open the build log and find the `VERIFY FAILED` block. It lists exactly what
  didn't match: a committed file's hash, a library version, or the example prediction. The previous
  deploy keeps running meanwhile.
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
2. Name `RENDER_SERVICE_URL`, value your service URL, e.g. `https://mindcare-api-fysd.onrender.com`
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

**The committed-artifact build (current), verified on 2026-10-04** in a clean copy of the repository
with a new Python 3.13.13 virtual environment from `requirements.txt`, and **no build step**, as on
Render:

- **The build command passes.** `python scripts/deploy_artifacts.py verify` matched all three
  hashes and both library versions, loaded the files through the real app, and reproduced the
  documented `/predict` example with a difference of 0.0 from the manifest.
- **It fails when it should.** In the clean copy it exited non-zero, with a clear message, for:
  - the model file altered by one byte (SHA-256 mismatch);
  - the model file missing;
  - a scikit-learn version different from the one that wrote the pickles.
- **The start command works with no build step.** `uvicorn src.api.main:app` from the clean copy
  served `/health` (`"ok"`), `/predict` (the documented example to every digit), `/form` and
  `/docs`. The working copy's model file was hidden during startup, to prove the server loaded the
  committed one.
- **Local regeneration still works.** `bash scripts/build_model_artifacts.sh` passed all 7 steps
  and then its final check, with the three served files byte-identical to the committed ones.
- **Render accepts `rootDir: "MindCare AI"`.** Its first deploy got through steps 1–5 inside that
  folder before failing at step 6, the failure that led to this approach.
- **The keep-alive script works** (2026-10-04): run locally against a healthy server, a stopped
  server, a server answering 200 with `"status":"not_ready"`, and with the URL unset. Only the
  healthy case passed; the other three failed with an error.

**Not verified yet:**
- **A Render deploy with the committed artifacts.** The next deploy from `main` is the first real
  run of this build on Render's Linux machine. Inference on Linux may differ from Windows in the
  last bits of a float; the check allows 1e-6 for that. If it fails anyway, the build log shows
  the actual difference.
- **Unpinned packages.** Only `scikit-learn` and `xgboost` are pinned in `requirements.txt`. Others
  (pandas, numpy, fastapi, uvicorn, ...) install at whatever version is newest when Render builds.
  The check would catch a newer version that changes the served prediction; pin the affected package
  to the version in the project's working environment if that happens.
- **The GitHub Actions run itself** (the script was run locally, not on GitHub's runners).

## Verify locally

Before relying on Render, run its build and start commands from inside `MindCare AI/`, in a fresh
virtual environment, as Render does:

```bash
python -m venv .venv_deploy_check
.venv_deploy_check/Scripts/python -m pip install -r requirements.txt
.venv_deploy_check/Scripts/python scripts/deploy_artifacts.py verify
.venv_deploy_check/Scripts/uvicorn src.api.main:app --host 127.0.0.1 --port 8010
```

Then open `http://127.0.0.1:8010/health`. On macOS/Linux use `.venv_deploy_check/bin`.
