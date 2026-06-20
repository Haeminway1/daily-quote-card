import { writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const WEBAPP_URL_PREFIX = 'https://script.google.com/macros/s/';

export function parseClaspDeployments(input) {
  const text = String(input || '').trim();
  if (!text) throw new Error('No clasp deployments output was provided.');

  const jsonDeployments = parseJsonDeployments(text);
  const deployments = jsonDeployments || parseTextDeployments(text);
  if (!deployments.length) {
    throw new Error('No deployment IDs were found in clasp deployments output.');
  }
  return deployments;
}

export function selectDeployment(deployments, track) {
  const normalizedTrack = normalizeTrack(track);
  const candidates = deployments
    .filter(deployment => deployment.track === normalizedTrack || deploymentDescriptionHasTrack(deployment.description, normalizedTrack))
    .sort((a, b) => Number(b.versionNumber || 0) - Number(a.versionNumber || 0));

  if (!candidates.length) {
    throw new Error(`No ${normalizedTrack} deployment was found in clasp deployments output.`);
  }
  return candidates[0];
}

function parseJsonDeployments(text) {
  try {
    const parsed = JSON.parse(text);
    const rawDeployments = Array.isArray(parsed)
      ? parsed
      : Array.isArray(parsed.deployments)
        ? parsed.deployments
        : Array.isArray(parsed.result)
          ? parsed.result
          : null;
    if (!rawDeployments) return null;
    return rawDeployments.map(normalizeJsonDeployment).filter(Boolean);
  } catch (_) {
    return null;
  }
}

function normalizeJsonDeployment(item) {
  if (!item || typeof item !== 'object') return null;
  const deploymentId = String(item.deploymentId || item.id || '').trim();
  if (!deploymentId) return null;
  const deploymentConfig = item.deploymentConfig && typeof item.deploymentConfig === 'object'
    ? item.deploymentConfig
    : {};
  const description = String(item.description || deploymentConfig.description || '').trim();
  const versionRaw = item.versionNumber || item.version || deploymentConfig.versionNumber || deploymentConfig.version || '';
  const versionNumber = normalizeVersion(versionRaw);
  return {
    deploymentId,
    versionNumber,
    description,
    track: trackFromDescription(description),
    webappUrl: String(item.webappUrl || item.webAppUrl || `${WEBAPP_URL_PREFIX}${deploymentId}/exec`).trim(),
  };
}

function parseTextDeployments(text) {
  return text
    .split(/\r?\n/u)
    .map(line => line.trim())
    .map((line) => {
      const idMatch = line.match(/\b(AKfyc[^\s,;]+)/u);
      if (!idMatch) return null;
      const deploymentId = idMatch[1].replace(/[)\].,;]+$/u, '');
      const versionMatch = line.match(/@(\d+|HEAD)\b/u) || line.match(/\bversion(?:Number)?\s*[:=]\s*(\d+|HEAD)\b/iu);
      const versionNumber = normalizeVersion(versionMatch?.[1] || '');
      const description = descriptionFromLine(line);
      return {
        deploymentId,
        versionNumber,
        description,
        track: trackFromDescription(description || line),
        webappUrl: `${WEBAPP_URL_PREFIX}${deploymentId}/exec`,
      };
    })
    .filter(Boolean);
}

function descriptionFromLine(line) {
  const dashIndex = line.indexOf(' - ');
  if (dashIndex >= 0) return line.slice(dashIndex + 3).trim();
  const descriptionMatch = line.match(/\bdescription\s*[:=]\s*(.+)$/iu);
  return descriptionMatch ? descriptionMatch[1].trim() : '';
}

function normalizeVersion(value) {
  const text = String(value || '').trim();
  if (!text || text === 'HEAD') return null;
  const number = Number(text);
  return Number.isInteger(number) && number >= 0 ? number : null;
}

function normalizeTrack(track) {
  const value = String(track || '').trim().toLowerCase();
  if (value === 'staging' || value === 'prod') return value;
  throw new Error(`Unsupported deployment track: ${track}. Expected staging or prod.`);
}

function trackFromDescription(description) {
  const text = String(description || '').toLowerCase();
  if (/\b(staging|stage|stg)\b/u.test(text)) return 'staging';
  if (/\b(prod|production)\b/u.test(text)) return 'prod';
  return '';
}

function deploymentDescriptionHasTrack(description, track) {
  return trackFromDescription(description) === normalizeTrack(track);
}

function readArg(flag) {
  const index = process.argv.indexOf(flag);
  return index >= 0 ? process.argv[index + 1] : '';
}

async function readStdin() {
  let input = '';
  for await (const chunk of process.stdin) input += chunk;
  return input;
}

async function main() {
  const track = readArg('--track');
  const idFile = readArg('--deployment-id-file');
  const urlFile = readArg('--webapp-url-file');
  const deployment = selectDeployment(parseClaspDeployments(await readStdin()), track);
  if (idFile) writeFileSync(idFile, `${deployment.deploymentId}\n`);
  if (urlFile) writeFileSync(urlFile, `${deployment.webappUrl}\n`);
  process.stdout.write(`${JSON.stringify(deployment)}\n`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(error.message);
    process.exit(1);
  });
}
