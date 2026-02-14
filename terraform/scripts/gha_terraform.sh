#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/gha_terraform.sh <env_name> <apply_flag>
#   env_name: stage | prod
#   apply_flag: true | false
ENV_NAME=${1:-}
APPLY_FLAG=${2:-false}

if [ -z "$ENV_NAME" ]; then
  echo "Usage: $0 <env_name> <apply_flag>"
  exit 1
fi

TF_BACKEND_CONFIG="backends/${ENV_NAME}.hcl"
TF_VAR_FILE="tfvars/${ENV_NAME}.tfvars"

echo "Terraform init with ${TF_BACKEND_CONFIG}"
terraform init -backend-config="${TF_BACKEND_CONFIG}"

echo "Terraform plan with ${TF_VAR_FILE}"
terraform plan -var-file="${TF_VAR_FILE}" -out=tfplan

if [ "$APPLY_FLAG" = "true" ]; then
  echo "Terraform apply"
  terraform apply -auto-approve tfplan
else
  echo "Skip apply (apply_flag=${APPLY_FLAG})"
fi
