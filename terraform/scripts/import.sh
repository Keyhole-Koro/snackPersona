#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/import.sh <tfvars_file>
TFVARS_FILE=${1:-}
if [ -z "$TFVARS_FILE" ]; then
  echo "Usage: $0 <tfvars_file>"
  exit 1
fi

TABLE_NAME=$(grep -E '^table_name' "$TFVARS_FILE" | cut -d'=' -f2 | tr -d ' "')
ENV=$(grep -E '^env' "$TFVARS_FILE" | cut -d'=' -f2 | tr -d ' "')

if [ "$ENV" = "local" ]; then
  export AWS_ENDPOINT_URL="http://localhost:4566"
  export AWS_REGION="us-east-1"
  export AWS_ACCESS_KEY_ID="test"
  export AWS_SECRET_ACCESS_KEY="test"
fi

import_if_missing() {
  local addr=$1
  local id=$2

  if terraform state list | grep -Fq "$addr"; then
    echo "skip: $addr already in state"
    return 0
  fi

  echo "import: $addr <- $id"
  terraform import -var-file="$TFVARS_FILE" "$addr" "$id" || true
}

import_if_missing "module.db.aws_dynamodb_table.snack_table" "$TABLE_NAME"
import_if_missing "module.simulation.aws_ecr_repository.simulation_repo" "snack-simulation-${ENV}"
import_if_missing "module.simulation.aws_ecs_cluster.snack_cluster" "snack-cluster-${ENV}"

echo "done"
