#!/usr/bin/env node
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { expandHome } from '../../../lib/gas-project-contract.mjs';
import { wrapperOrigin } from '../../../lib/gas-project-wrapper-contract.mjs';
import { buildWrapperLocal } from './build-wrapper-local.mjs';

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(SCRIPT_DIR, '..');

function parseArgs(argv) {
  const options = { project: PROJECT_ROOT, dryRun: true, dryRunExplicit: false, confirm: false, branch: 'main' };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--project') options.project = argv[++index];
    else if (arg === '--dry-run') {
      options.dryRun = true;
      options.dryRunExplicit = true;
    } else if (arg === '--wrapper-confirm') {
      options.confirm = true;
      if (!options.dryRunExplicit) options.dryRun = false;
    } else if (arg === '--branch') options.branch = argv[++index];
    else if (arg === '-h' || arg === '--help') options.help = true;
    else throw new Error(`Unknown argument: ${arg}`);
  }
  return options;
}

function loadContract(projectRoot) {
  return JSON.parse(readFileSync(join(projectRoot, 'gas.project.json'), 'utf8'));
}

function deploymentCommand(buildDir, projectName, branch) {
  return ['wrangler', 'pages', 'deploy', buildDir, `--project-name=${projectName}`, `--branch=${branch}`];
}

function writeWrapperUrl(contract) {
  const runtimeDir = resolve(expandHome(process.env.GAS_DEV_RUNTIME_DIR || contract.runtimeDir));
  const url = wrapperOrigin(contract);
  const file = join(runtimeDir, '.wrapper-url');
  writeFileSync(file, `${url}\n`, 'utf8');
  return file;
}

function deployWithWrangler(command) {
  return spawnSync('npx', command, {
    cwd: PROJECT_ROOT,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
}

export function deployWrapperLocal(options = {}) {
  const deployOptions = {
    project: options.project || PROJECT_ROOT,
    branch: options.branch || 'main',
    confirm: Boolean(options.confirm),
    dryRun: options.dryRun === undefined ? !Boolean(options.confirm) : Boolean(options.dryRun),
  };
  const projectRoot = resolve(deployOptions.project);
  const contract = loadContract(projectRoot);
  const build = buildWrapperLocal({ projectRoot });
  const wrapper = contract.wrapper;
  const command = deploymentCommand(build.outputDir, wrapper.projectName, deployOptions.branch);

  if (!deployOptions.dryRun && !deployOptions.confirm) {
    return {
      ok: false,
      dryRun: false,
      deployed: false,
      reason: 'wrapper_confirm_required',
      projectName: wrapper.projectName,
      url: build.url,
      buildDir: build.outputDir,
      command: ['npx', ...command],
    };
  }

  const result = {
    ok: true,
    dryRun: deployOptions.dryRun,
    deployed: false,
    reason: deployOptions.dryRun ? 'dry_run' : 'ready_to_deploy',
    projectName: wrapper.projectName,
    url: build.url,
    buildDir: build.outputDir,
    command: ['npx', ...command],
  };

  if (!existsSync(build.outputDir)) throw new Error(`wrapper build missing: ${build.outputDir}`);
  if (deployOptions.dryRun) return result;

  const deploy = deployWithWrangler(command);
  if (deploy.status !== 0) {
    return { ...result, ok: false, reason: 'wrangler_deploy_failed', stdout: deploy.stdout, stderr: deploy.stderr };
  }
  const urlFile = writeWrapperUrl(contract);
  return { ...result, dryRun: false, deployed: true, reason: 'deployed', urlFile, stdout: deploy.stdout };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try {
    const options = parseArgs(process.argv.slice(2));
    if (options.help) {
      console.log('Usage: deploy-wrapper-local.mjs [--project <path>] [--dry-run] [--wrapper-confirm] [--branch main]');
      process.exit(0);
    }
    const result = deployWrapperLocal(options);
    console.log(JSON.stringify(result, null, 2));
    process.exit(result.ok ? 0 : 1);
  } catch (error) {
    console.error(`error: ${error.message}`);
    process.exit(1);
  }
}
