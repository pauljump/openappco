// Renders app status for the README and openappco.com from GitHub issues.
// Issue labels own status. scripts/asc-status.py (Mini, read-only App Store
// Connect) keeps labels and the "App Store:" body line current; this script adds
// public App Store availability (iTunes lookup, no credentials) and, with
// --promote, flips an app to status:live once Apple actually lists it.
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';

const repo = 'pauljump/openappco';
const promote = process.argv.includes('--promote');
const config = JSON.parse(readFileSync(new URL('../apps.config.json', import.meta.url), 'utf8'));
const gh = args => execFileSync('gh', args, { encoding: 'utf8' });
const issues = JSON.parse(gh(['issue', 'list', '--repo', repo, '--label', 'app', '--state', 'open', '--limit', '200', '--json', 'number,title,url,body,labels,reactionGroups']));
const statuses = { 'status:building': 'Building', 'status:in-review': 'In review', 'status:live': 'Live' };
const clean = s => s.replaceAll('|', '\\|').replace(/[\r\n]/g, ' ');

async function lookup(ascId) {
  if (!ascId) return null;
  try {
    const r = await fetch(`https://itunes.apple.com/lookup?id=${ascId}&country=us`, { signal: AbortSignal.timeout(10000) });
    const hit = (await r.json()).results?.[0];
    return hit ? { url: hit.trackViewUrl.split('?')[0], version: hit.version, released: hit.currentVersionReleaseDate } : null;
  } catch { return null; }
}

// Fine-grained App Store Connect state -> public stage (4 steps on the site).
function stageFor(label, ascState) {
  if (label === 'status:live') return 'live';
  if (label === 'status:building') return ascState?.includes('REJECTED') ? 'changes' : 'building';
  if (ascState === 'IN_REVIEW') return 'review';
  if (['PENDING_DEVELOPER_RELEASE', 'PENDING_APPLE_RELEASE', 'PROCESSING_FOR_APP_STORE'].includes(ascState)) return 'approved';
  return 'submitted';
}

const apps = [];
for (const i of issues.sort((a, b) => a.title.localeCompare(b.title))) {
  let labels = i.labels.map(l => l.name).filter(l => statuses[l]);
  if (labels.length !== 1) throw new Error(`Expected one status: ${i.title}`);
  const next = i.body.match(/^Next: (.+)$/m)?.[1];
  if (!next) throw new Error(`Missing Next line: ${i.title}`);
  const asc = i.body.match(/^App Store: ([A-Z_]+) · checked (\S+)$/m);
  const meta = config.apps.find(a => a.issue === i.number) || {};
  const store = await lookup(meta.ascId);
  if (store && labels[0] !== 'status:live' && promote) {
    gh(['issue', 'edit', String(i.number), '--repo', repo, '--add-label', 'status:live', '--remove-label', labels[0]]);
    labels = ['status:live'];
  }
  const likes = i.reactionGroups?.find(g => g.content === 'THUMBS_UP')?.users?.totalCount ?? 0;
  apps.push({ ...meta, issue: i.number, issueUrl: i.url, name: i.title, label: labels[0], status: statuses[labels[0]],
    stage: store ? 'live' : stageFor(labels[0], asc?.[1]), ascState: asc?.[1] ?? null, ascChecked: asc?.[2] ?? null,
    next, likes, store });
}
if (!apps.length) throw new Error('No app issues found');

// Keep the old timestamp when nothing changed, so scheduled runs make no commit.
const out = new URL('../docs/apps.json', import.meta.url);
let previous = {};
try { previous = JSON.parse(readFileSync(out, 'utf8')); } catch {}
const same = JSON.stringify({ apps, teasers: config.teasers }) === JSON.stringify({ apps: previous.apps, teasers: previous.teasers });
writeFileSync(out, JSON.stringify({ generated: same ? previous.generated : new Date().toISOString(), apps, teasers: config.teasers }, null, 2) + '\n');

const path = new URL('../README.md', import.meta.url);
const rows = apps.map(a => `| [${clean(a.name)}](${a.issueUrl}) | ${a.store ? `[Live](${a.store.url})` : a.status} | ${clean(a.next)} |`);
const table = ['<!-- apps:start -->', '| App | Status | Next |', '| --- | --- | --- |', ...rows, '<!-- apps:end -->'].join('\n');
writeFileSync(path, readFileSync(path, 'utf8').replace(/<!-- apps:start -->[\s\S]*?<!-- apps:end -->/, table));
console.log(`Updated ${apps.length} apps`);
