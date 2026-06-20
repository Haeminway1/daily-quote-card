#!/usr/bin/env node
import { copyFileSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expandHome, validateProjectContract } from '../../../lib/gas-project-contract.mjs';
import { wrapperOrigin } from '../../../lib/gas-project-wrapper-contract.mjs';

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(SCRIPT_DIR, '..');
const WRAPPER_DIR = join(PROJECT_ROOT, 'wrapper');
const TEXT_FILES = ['README.md', 'index.html', 'config.js', 'manifest.webmanifest', 'sw.js'];
const ICON_FILES = ['apple-touch-icon.png', 'icon-192.png', 'icon-512.png', 'icon-source.png'];

function parseArgs(argv) {
  const options = { project: PROJECT_ROOT, json: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--project') options.project = argv[++index];
    else if (arg === '--json') options.json = true;
    else if (arg === '-h' || arg === '--help') options.help = true;
    else throw new Error(`Unknown argument: ${arg}`);
  }
  return options;
}

function loadContract(projectRoot) {
  return JSON.parse(readFileSync(join(projectRoot, 'gas.project.json'), 'utf8'));
}

function requireWrapper(contract) {
  const wrapper = contract.wrapper;
  if (!wrapper || wrapper.enabled === false || wrapper.host === 'none') {
    throw new Error('gas.project.json wrapper.enabled must be true for wrapper build.');
  }
  return wrapper;
}

function resolveGasUrl() {
  const gasUrl = (process.env.GAS_WEBAPP_URL || process.env.WEBAPP_URL || '').trim();
  if (!gasUrl) return '';
  try {
    const parsed = new URL(gasUrl);
    if (parsed.origin === 'https://script.google.com' && /^\/macros\/s\/[^/]+\/exec\/?$/.test(parsed.pathname)) {
      return parsed.toString();
    }
  } catch (_) {
    // Fall through to the deployment-safe error below.
  }
  throw new Error('GAS_WEBAPP_URL must be a valid Apps Script /exec URL.');
}

function buildValues(contract, wrapper) {
  const origin = wrapperOrigin(contract);
  if (!origin) throw new Error('wrapper origin could not be resolved.');
  return {
    SLUG: contract.slug,
    APP_NAME: wrapper.appName,
    SHORT_NAME: wrapper.shortName,
    THEME_COLOR: wrapper.themeColor,
    GAS_URL: resolveGasUrl(),
    GAS_ORIGIN: 'https://script.google.com',
    WRAPPER_ORIGIN: origin,
  };
}

function renderTemplate(source, values) {
  let content = readFileSync(source, 'utf8');
  for (const [key, value] of Object.entries(values)) {
    content = content.replaceAll(`__${key}__`, String(value));
  }
  if (/__[A-Z0-9_]+__/.test(content)) {
    throw new Error(`Unresolved wrapper token in ${source}`);
  }
  return content;
}

function runtimeDir(contract) {
  return resolve(expandHome(process.env.GAS_DEV_RUNTIME_DIR || contract.runtimeDir));
}

function copyIcons(projectRoot, outputDir) {
  for (const name of ICON_FILES) {
    const source = join(projectRoot, 'wrapper', name);
    if (!existsSync(source)) throw new Error(`Missing project wrapper icon asset: ${name}`);
    copyFileSync(source, join(outputDir, name));
  }
}

export function buildWrapperLocal({ projectRoot = PROJECT_ROOT } = {}) {
  const root = resolve(projectRoot);
  const contract = loadContract(root);
  const validation = validateProjectContract(contract, { projectRoot: root });
  if (!validation.ok) throw new Error(validation.errors.join('\n'));

  const wrapper = requireWrapper(contract);
  const outputDir = join(runtimeDir(contract), 'wrapper-build');
  const values = buildValues(contract, wrapper);

  rmSync(outputDir, { recursive: true, force: true });
  mkdirSync(outputDir, { recursive: true });
  for (const name of TEXT_FILES) {
    writeFileSync(join(outputDir, name), renderTemplate(join(root, 'wrapper', name), values), 'utf8');
  }
  copyIcons(root, outputDir);
  return { ok: true, outputDir, projectName: wrapper.projectName, url: values.WRAPPER_ORIGIN };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try {
    const options = parseArgs(process.argv.slice(2));
    if (options.help) {
      console.log('Usage: build-wrapper-local.mjs [--project <path>] [--json]');
      process.exit(0);
    }
    const result = buildWrapperLocal({ projectRoot: options.project });
    if (options.json) console.log(JSON.stringify(result, null, 2));
    else console.log(`Built wrapper at ${result.outputDir}`);
  } catch (error) {
    console.error(`error: ${error.message}`);
    process.exit(1);
  }
}
