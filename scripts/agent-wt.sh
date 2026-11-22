#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <feature-id> <slug> [--no-gemini]"
  echo "Example: $0 app-16 semantic-enrichment"
  exit 1
}

[ $# -lt 2 ] && usage

RAW_ID="$1"
SLUG="$2"
LAUNCH_GEMINI=true
if [ "${3:-}" = "--no-gemini" ]; then
  LAUNCH_GEMINI=false
fi

# Normalize IDs like APP-16 -> app-16 for paths/branches
ID_LOWER=$(echo "$RAW_ID" | tr '[:upper:]' '[:lower:]')
REPO_ROOT=$(git rev-parse --show-toplevel)
WT_PATH="${REPO_ROOT}/../spinsleeve-${ID_LOWER}"
BRANCH_NAME="feat/${ID_LOWER}-${SLUG}"

if [ ! -d "$WT_PATH" ]; then
  if git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}"; then
    git worktree add "$WT_PATH" "$BRANCH_NAME"
  else
    git worktree add "$WT_PATH" -b "$BRANCH_NAME"
  fi
fi

echo "Worktree ready: $WT_PATH (branch: $BRANCH_NAME)"
cd "$WT_PATH"

if [ "$LAUNCH_GEMINI" = true ]; then
  exec gemini
fi
