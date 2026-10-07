#!/usr/bin/env bash
# Rebuild every model artifact from the raw CSV, in the order docs/setup.md specifies.
# For LOCAL DEVELOPMENT. Render does not run this: it serves the three committed artifacts and only
# checks them (scripts/deploy_artifacts.py verify), because XGBoost retrained on Render's Linux
# machine is not bit-identical to the validated build (docs/deployment.md).
#
# Most .pkl/.npz artifacts are gitignored, so a fresh clone has none of them; the three served ones
# are committed. Every input these steps need IS in git: data/raw/mindcare_dataset_final.csv,
# data/processed/mindcare_processed_splits.npz (the one tracked split), and
# reports/tuning_results_3class.json / reports/tuning_results_12feature.json.
#
# Each step verifies its own output against documented numbers and exits non-zero on a mismatch;
# `set -e` turns that into a failed build. The last check compares the rebuilt served artifacts
# with the committed, deployed ones (data/processed/deploy_artifacts.json).
#
# Usage (from inside MindCare AI/, with the project's Python on PATH):
#   bash scripts/build_model_artifacts.sh
set -euo pipefail

cd "$(dirname "$0")/.."

run_step() {
  local number="$1" module="$2"
  echo "=== Step ${number}/7: python -m ${module}"
  local start=$SECONDS
  python -m "${module}"
  echo "=== Step ${number}/7 done in $((SECONDS - start))s"
}

run_step 1 src.rebuild_preprocessor
run_step 2 src.build_3class_target
run_step 3 src.models.save_final_model
run_step 4 src.models.adopt_11feature_model
run_step 5 src.models.adopt_12feature_model
run_step 6 src.models.adopt_xgboost_12feature_model
run_step 7 src.models.adopt_11feature_v2_model

# The API loads exactly these three files (plus the tracked recommendation templates).
for artifact in \
  data/processed/mindcare_label_encoder_3class.pkl \
  data/processed/mindcare_preprocessor_11feature_v2.pkl \
  data/processed/mindcare_final_model_11feature_v2_xgb.pkl \
  data/processed/recommendation_templates.json; do
  if [ ! -s "${artifact}" ]; then
    echo "ERROR: ${artifact} is missing after the build" >&2
    exit 1
  fi
done
echo "=== All 7 steps passed; the API's artifacts are in place."

# Steps 2 and 7 rewrote the three committed, deployed artifacts. On the platform and library versions
# that built them this is byte-identical; anywhere else it may not be.
echo "=== Checking the rebuilt served artifacts against the committed deployment manifest"
if ! python scripts/deploy_artifacts.py verify; then
  cat >&2 <<'MSG'
NOTE: the rebuilt served artifacts differ from the committed, deployed ones (different platform or
library versions). Local work is fine, but do NOT commit them unless you are deliberately adopting a
new model; restore the committed files with:
  git checkout -- data/processed/mindcare_label_encoder_3class.pkl data/processed/mindcare_preprocessor_11feature_v2.pkl data/processed/mindcare_final_model_11feature_v2_xgb.pkl
To deliberately adopt new served artifacts: python scripts/deploy_artifacts.py write, then commit
the three files and data/processed/deploy_artifacts.json together (docs/deployment.md).
MSG
  exit 1
fi
