#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

runtime_dir() {
  node --input-type=module -e '
    import { readFileSync } from "node:fs";
    import { homedir } from "node:os";
    import { join, resolve } from "node:path";
    const contract = JSON.parse(readFileSync("gas.project.json", "utf8"));
    const raw = process.env.GAS_DEV_RUNTIME_DIR || contract.runtimeDir;
    const expanded = raw === "~" ? homedir() : raw.startsWith("~/") ? join(homedir(), raw.slice(2)) : raw;
    console.log(resolve(expanded));
  '
}

RUNTIME_DIR="$(runtime_dir)"
BUILD_DIR="$RUNTIME_DIR/build"
CLASP_DIR="$RUNTIME_DIR/clasp"
STAGING_DEPLOYMENT_FILE="$RUNTIME_DIR/.deployment-id.staging"
PROD_DEPLOYMENT_FILE="$RUNTIME_DIR/.deployment-id.prod"
PREV_PROD_VERSION_FILE="$RUNTIME_DIR/.deployment-prev.prod"
STAGING_WEBAPP_FILE="$RUNTIME_DIR/.webapp-url.staging"
PROD_WEBAPP_FILE="$RUNTIME_DIR/.webapp-url.prod"
PARSER="$ROOT/tools/clasp-deployments.mjs"

usage() {
  cat <<'USAGE'
Usage:
  ./deploy.sh build
  ./deploy.sh wrapper-build
  ./deploy.sh wrapper-deploy [--dry-run]
  ./deploy.sh deploy [--dry-run]              # deploys staging only
  ./deploy.sh promote --prod-confirm [--dry-run]
  ./deploy.sh rollback --prod-confirm [--dry-run]

Production promote/rollback require --prod-confirm. Do not run them against a live
customer app without owner approval.
USAGE
}

build_payload() {
  mkdir -p "$BUILD_DIR" "$CLASP_DIR"
  python3 "$ROOT/compile_code.py"
  cp "$BUILD_DIR/Code.js" "$CLASP_DIR/Code.js"
  cp "$BUILD_DIR/index.html" "$CLASP_DIR/index.html"
  cp "$BUILD_DIR/appsscript.json" "$CLASP_DIR/appsscript.json"
  migrate_legacy_state
  echo "Build copied to $CLASP_DIR"
}

migrate_legacy_state() {
  if [[ -f "$CLASP_DIR/.deployment-id" && ! -f "$STAGING_DEPLOYMENT_FILE" ]]; then
    mv "$CLASP_DIR/.deployment-id" "$STAGING_DEPLOYMENT_FILE"
  fi
  if [[ -f "$CLASP_DIR/.webapp-url" && ! -f "$STAGING_WEBAPP_FILE" ]]; then
    mv "$CLASP_DIR/.webapp-url" "$STAGING_WEBAPP_FILE"
  fi
}

require_confirm() {
  local confirm="${1:-}"
  if [[ "$confirm" != "--prod-confirm" ]]; then
    echo "error: prod command requires --prod-confirm" >&2
    exit 2
  fi
}

run_clasp() {
  npx clasp "$@"
}

deploy_staging() {
  local dry_run="$1"
  build_payload
  if [[ "$dry_run" == "1" ]]; then
    echo "dry-run: would push and deploy staging from $CLASP_DIR"
    return
  fi
  (cd "$CLASP_DIR" && run_clasp push -f)
  if [[ -s "$STAGING_DEPLOYMENT_FILE" ]]; then
    (cd "$CLASP_DIR" && run_clasp deploy -i "$(tr -d '\n' < "$STAGING_DEPLOYMENT_FILE")" -d "staging")
  else
    (cd "$CLASP_DIR" && run_clasp deploy -d "staging")
  fi
  refresh_deployments staging
}

promote_prod() {
  local dry_run="$1"
  build_payload
  if [[ "$dry_run" == "1" ]]; then
    echo "dry-run: would run local gates and promote staging deployment to prod"
    echo "dry-run: would save current prod version to $PREV_PROD_VERSION_FILE"
    return
  fi
  npm run test:project-contract
  npm run test:runtime-build
  npm run test:mobile:local
  local previous_version
  previous_version="$(read_track_version prod || true)"
  if [[ -n "$previous_version" ]]; then
    printf '%s\n' "$previous_version" > "$PREV_PROD_VERSION_FILE"
  fi
  (cd "$CLASP_DIR" && run_clasp push -f)
  if [[ -s "$PROD_DEPLOYMENT_FILE" ]]; then
    (cd "$CLASP_DIR" && run_clasp deploy -i "$(tr -d '\n' < "$PROD_DEPLOYMENT_FILE")" -d "prod")
  else
    (cd "$CLASP_DIR" && run_clasp deploy -d "prod")
  fi
  refresh_deployments prod
}

rollback_prod() {
  local dry_run="$1"
  if [[ ! -s "$PREV_PROD_VERSION_FILE" ]]; then
    echo "error: no previous prod version recorded at $PREV_PROD_VERSION_FILE" >&2
    exit 2
  fi
  if [[ ! -s "$PROD_DEPLOYMENT_FILE" ]]; then
    echo "error: no prod deployment ID recorded at $PROD_DEPLOYMENT_FILE" >&2
    exit 2
  fi
  local previous_version
  previous_version="$(tr -d '\n' < "$PREV_PROD_VERSION_FILE")"
  if [[ "$dry_run" == "1" ]]; then
    echo "dry-run: would rollback prod deployment $(tr -d '\n' < "$PROD_DEPLOYMENT_FILE") to version $previous_version"
    return
  fi
  (cd "$CLASP_DIR" && run_clasp deploy -i "$(tr -d '\n' < "$PROD_DEPLOYMENT_FILE")" -V "$previous_version" -d "prod-rollback")
  refresh_deployments prod
}

refresh_deployments() {
  local track="$1"
  case "$track" in
    staging)
      (cd "$CLASP_DIR" && run_clasp deployments) | node "$PARSER" --track staging --deployment-id-file "$STAGING_DEPLOYMENT_FILE" --webapp-url-file "$STAGING_WEBAPP_FILE" >/dev/null
      ;;
    prod)
      (cd "$CLASP_DIR" && run_clasp deployments) | node "$PARSER" --track prod --deployment-id-file "$PROD_DEPLOYMENT_FILE" --webapp-url-file "$PROD_WEBAPP_FILE" >/dev/null
      ;;
    *)
      echo "error: unknown deployment track $track" >&2
      exit 2
      ;;
  esac
}

read_track_version() {
  local track="$1"
  (cd "$CLASP_DIR" && run_clasp deployments) | node "$PARSER" --track "$track" | node --input-type=module -e '
    let input = "";
    for await (const chunk of process.stdin) input += chunk;
    const deployment = JSON.parse(input);
    if (!Number.isInteger(deployment.versionNumber)) process.exit(1);
    process.stdout.write(String(deployment.versionNumber));
  '
}

command="${1:-help}"
case "$command" in
  build)
    build_payload
    ;;
  deploy)
    dry_run=0
    [[ "${2:-}" == "--dry-run" ]] && dry_run=1
    deploy_staging "$dry_run"
    ;;
  wrapper-build)
    npm run wrapper:build
    ;;
  wrapper-deploy)
    shift
    npm run wrapper:deploy -- "$@"
    ;;
  promote)
    require_confirm "${2:-}"
    dry_run=0
    [[ "${3:-}" == "--dry-run" ]] && dry_run=1
    promote_prod "$dry_run"
    ;;
  rollback)
    require_confirm "${2:-}"
    dry_run=0
    [[ "${3:-}" == "--dry-run" ]] && dry_run=1
    rollback_prod "$dry_run"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
