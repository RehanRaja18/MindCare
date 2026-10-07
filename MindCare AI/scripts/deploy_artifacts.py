"""Committed deployment artifacts: write their manifest, or verify them.

Render does NOT retrain the model. Retraining XGBoost on Render's Linux build machine does not
reproduce the Windows-built model bit for bit (multi-threaded tree building differs slightly
across platforms), so step 6 of the regeneration scripts failed its exact-match check there. The
three files the API serves are therefore committed to git, as a deployment-only exception to the
"model artifacts are not in git" policy (docs/deployment.md, "Why the served model is committed"):

    data/processed/mindcare_label_encoder_3class.pkl
    data/processed/mindcare_preprocessor_11feature_v2.pkl
    data/processed/mindcare_final_model_11feature_v2_xgb.pkl

    python scripts/deploy_artifacts.py write    # after deliberately adopting new artifacts
    python scripts/deploy_artifacts.py verify   # Render's build command; also safe to run locally

`write` records each file's SHA-256 and size, the Python / scikit-learn / xgboost versions that
produced them, and the API's response to the worked example in docs/api_usage.md, into
data/processed/deploy_artifacts.json.

`verify` fails (non-zero exit) unless:
  1. each committed file exists and matches the manifest's SHA-256 (they are the validated files);
  2. the installed scikit-learn and xgboost versions equal the ones that wrote the pickles;
  3. the real app (src/api/main.py, via FastAPI's TestClient) loads them, /health reports "ok",
     /predict returns the manifest's prediction for the worked example (same class and labels,
     probabilities within PROBABILITY_TOLERANCE), and /patient-summary returns 200 with its caveat.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # so `import src...` works when run as `python scripts/deploy_artifacts.py`

MANIFEST_PATH = ROOT / "data" / "processed" / "deploy_artifacts.json"
ARTIFACTS = [
    "data/processed/mindcare_label_encoder_3class.pkl",
    "data/processed/mindcare_preprocessor_11feature_v2.pkl",
    "data/processed/mindcare_final_model_11feature_v2_xgb.pkl",
]
# Inference on another platform may differ in the last bits of a float; anything beyond this is a
# different model, not rounding.
PROBABILITY_TOLERANCE = 1e-6

# The worked example from docs/api_usage.md ("Full worked example").
EXAMPLE = {
    "Age": 34, "Sleep Hours": 8.2, "Physical Activity (hrs/week)": 5.5,
    "cups_of_coffee": 1, "cups_of_tea": 0, "energy_drinks": 0, "cans_of_soda": 0,
    "pss_uncontrollable": 0, "pss_confident": 3, "pss_going_your_way": 4, "pss_difficulties_piling_up": 0,
    "Heart Rate (bpm)": 68, "Breathing Rate (breaths/min)": 14, "Therapy Sessions (per month)": 0,
    "Diet Quality (1-10)": 9, "Occupation": "Teacher", "Family History of Anxiety": "No",
}
PREDICTION_FIELDS = ["predicted_class", "probabilities", "uncertainty_flag", "estimated_caffeine_mg",
                     "estimated_stress_level", "confidence_label", "borderline_between"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def library_versions() -> dict[str, str]:
    import sklearn
    import xgboost
    return {"python": platform.python_version(), "scikit-learn": sklearn.__version__, "xgboost": xgboost.__version__}


def call_app() -> dict:
    from fastapi.testclient import TestClient

    from src.api.main import MODEL_PATH, PREPROCESSOR_PATH, app

    with TestClient(app) as client:  # the context manager runs startup, which loads the artifacts
        health = client.get("/health").json()
        prediction = client.post("/predict", json=EXAMPLE)
        summary = client.post("/patient-summary", json=EXAMPLE)
    return {"health": health, "prediction_status": prediction.status_code, "prediction": prediction.json(),
            "summary_status": summary.status_code, "summary": summary.json(),
            "loaded": [str(PREPROCESSOR_PATH.relative_to(ROOT)).replace("\\", "/"),
                       str(MODEL_PATH.relative_to(ROOT)).replace("\\", "/")]}


def write() -> None:
    missing = [a for a in ARTIFACTS if not (ROOT / a).is_file()]
    if missing:
        raise SystemExit(f"Missing artifacts {missing}: build them first (docs/setup.md).")
    result = call_app()
    if result["health"].get("status") != "ok" or result["prediction_status"] != 200:
        raise SystemExit(f"The app does not serve these artifacts correctly: {result['health']}, HTTP {result['prediction_status']}")
    manifest = {
        "purpose": "Deployment-only exception: these are the validated files the API serves on Render. "
                   "See docs/deployment.md, 'Why the served model is committed'.",
        "built_with": library_versions(),
        "artifacts": {a: {"sha256": sha256(ROOT / a), "bytes": (ROOT / a).stat().st_size} for a in ARTIFACTS},
        "example_request": EXAMPLE,
        "expected_prediction": {k: result["prediction"][k] for k in PREDICTION_FIELDS},
        "expected_summary_tier": result["summary"]["estimated_severity_tier"],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {MANIFEST_PATH.relative_to(ROOT)} for {len(ARTIFACTS)} artifacts "
          f"(built with {manifest['built_with']}).")


def verify() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    problems: list[str] = []

    print("--- 1. Committed files match the manifest")
    for name, expected in manifest["artifacts"].items():
        path = ROOT / name
        if not path.is_file():
            problems.append(f"{name} is missing (is it committed? see the .gitignore exceptions)")
            print(f"  MISSING  {name}")
            continue
        ok = sha256(path) == expected["sha256"]
        print(f"  {'OK      ' if ok else 'MISMATCH'} {name} ({path.stat().st_size} bytes)")
        if not ok:
            problems.append(f"{name} differs from the validated file (SHA-256 mismatch)")

    print("--- 2. Installed libraries match the ones that wrote the pickles")
    installed, built = library_versions(), manifest["built_with"]
    for lib in ("scikit-learn", "xgboost"):
        ok = installed[lib] == built[lib]
        print(f"  {'OK      ' if ok else 'MISMATCH'} {lib}: installed {installed[lib]}, built with {built[lib]}")
        if not ok:
            problems.append(f"{lib} {installed[lib]} is installed but the pickles were written with {built[lib]}")
    print(f"  (python: installed {installed['python']}, built with {built['python']})")

    if problems:
        raise SystemExit("VERIFY FAILED:\n  - " + "\n  - ".join(problems))

    print("--- 3. The app serves the documented example")
    result = call_app()
    expected = manifest["expected_prediction"]
    got = result["prediction"]
    print(f"  loaded: {', '.join(result['loaded'])}")
    print(f"  /health: {result['health']}")
    if result["health"].get("status") != "ok":
        problems.append(f"/health is not ok: {result['health']}")
    if result["prediction_status"] != 200:
        problems.append(f"/predict returned HTTP {result['prediction_status']}: {got}")
    else:
        diff = max(abs(got["probabilities"][c] - expected["probabilities"][c]) for c in expected["probabilities"])
        print(f"  /predict: {got['predicted_class']} {got['probabilities']} (max difference from manifest {diff:.1e})")
        if diff > PROBABILITY_TOLERANCE:
            problems.append(f"probabilities differ from the manifest by {diff:.1e} (> {PROBABILITY_TOLERANCE})")
        for field in PREDICTION_FIELDS:
            if field != "probabilities" and got[field] != expected[field]:
                problems.append(f"/predict {field} is {got[field]!r}, expected {expected[field]!r}")
    if result["summary_status"] != 200 or not result["summary"].get("caveat"):
        problems.append(f"/patient-summary failed: HTTP {result['summary_status']}")
    elif result["summary"]["estimated_severity_tier"] != manifest["expected_summary_tier"]:
        problems.append(f"/patient-summary tier is {result['summary']['estimated_severity_tier']!r}, "
                        f"expected {manifest['expected_summary_tier']!r}")
    else:
        print(f"  /patient-summary: 200, tier {result['summary']['estimated_severity_tier']}, caveat present")

    if problems:
        raise SystemExit("VERIFY FAILED:\n  - " + "\n  - ".join(problems))
    print("=== Deployment artifacts verified: the committed model loads and serves the documented prediction.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "write":
        write()
    elif command == "verify":
        verify()
    else:
        raise SystemExit("usage: python scripts/deploy_artifacts.py write|verify")
