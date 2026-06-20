# Deployment: 좋은생각카드

This project supports local build, GAS deployment, and Cloudflare Pages wrapper deployment. Live GAS and real Cloudflare Pages deployment are owner-gated; the 2026-06-15 pass was explicitly owner-approved and completed.

## Local Build

```bash
npm run build
```

Runtime output is written under:

```text
~/dev/runtime/gas-dev/workspaces/gas_dev/projects/quotecard/
```

Source output directories such as `clasp/`, `export/`, `build/`, `.webapp-url*`, `.deployment-id*`, `.wrapper-url`, `.clasprc.json`, and `.env*` must remain local runtime state and must not be committed.

## GAS Deploy Boundary

Do not run these commands without explicit owner approval:

```bash
./deploy.sh deploy
clasp push
clasp deploy
```

Before any approved live deploy, rerun:

```bash
npm run test:project-contract
npm run build
npm run test:runtime-build
npm run test:deploy-state
npm run test:adaptive:local
npm run test:mobile:local
node ~/dev/agent-foundry/kits/gas-dev/hooks/gas_preflight.mjs --project . --strict-deploy
```

## Cloudflare Wrapper

The wrapper target is:

```text
projectName: gas-quotecard
origin: https://gas-quotecard.pages.dev
```

Verified local commands:

```bash
npm run wrapper:build
```

The 2026-06-15 production wrapper deployment evidence is `.omo/evidence/deploy-20260615-wrapper-deploy-prod.json`; it reports `dryRun: false`, `deployed: true`, and `projectName: gas-quotecard`.

The Cloudflare Pages project `gas-quotecard` was created on 2026-06-15 and deployed to:

```text
https://gas-quotecard.pages.dev
```

Do not run another real wrapper deployment without owner approval:

```bash
bash deploy.sh wrapper-deploy --wrapper-confirm
```

## Handoff State

- Local app build: verified.
- Mobile/adaptive viewport gates: verified.
- Card draw browser QA: verified.
- Wrapper local setup/frame QA: verified.
- GAS live deploy: completed on 2026-06-15.
- Cloudflare Pages project creation/deploy: completed on 2026-06-15.
- Git commit: not created in this pass because the current thread has unrelated dirty workspace state and the user did not explicitly request a commit.
