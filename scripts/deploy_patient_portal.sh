#!/usr/bin/env bash
# Build patient-dashboard and sync to the patient-portal S3 bucket (Member 3 / team guide).
# Run from repo root. Requires: AWS CLI, Node/npm, Terraform outputs in infrastructure/.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INFRA="${REPO_ROOT}/infrastructure"
APP="${REPO_ROOT}/frontend/apps/patient-dashboard"

cd "$INFRA"
API_URL="$(terraform output -raw api_gateway_url 2>/dev/null || true)"
POOL="$(terraform output -raw cognito_user_pool_id 2>/dev/null || true)"
PCLIENT="$(terraform output -raw cognito_patient_client_id 2>/dev/null || true)"
BUCKET="$(terraform output -raw s3_bucket_corpus 2>/dev/null || true)"
CF_ID="$(terraform output -raw patient_portal_cf_id 2>/dev/null || true)"

if [[ -z "${BUCKET}" ]]; then
  echo "Error: s3_bucket_corpus not found. Apply Terraform in infrastructure/ or set bucket manually." >&2
  exit 1
fi

export VITE_API_URL="${API_URL}"
export VITE_USE_MOCK="false"
export VITE_COGNITO_REGION="ap-south-1"
if [[ -n "${POOL}" && -n "${PCLIENT}" ]]; then
  export VITE_COGNITO_USER_POOL_ID="${POOL}"
  export VITE_COGNITO_CLIENT_ID="${PCLIENT}"
fi

cd "$APP"
npm install
npm run build

aws s3 sync dist/ "s3://${BUCKET}/" --delete --region ap-south-1

aws s3 website "s3://${BUCKET}/" --index-document index.html --error-document index.html --region ap-south-1

if [[ -n "${CF_ID}" ]]; then
  aws cloudfront create-invalidation --distribution-id "${CF_ID}" --paths "/*" --region ap-south-1
fi

echo "Done. Patient bucket: s3://${BUCKET}/"
