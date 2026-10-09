// The release lineup: slots 1-10, ranked by severity of one-star reviews.
//
//   node scripts/lineup.mjs propose            print the proposed lineup and the diff
//   node scripts/lineup.mjs propose --publish  open/refresh the "Lineup review" issue
//                                              (closes it when nothing changed)
//   node scripts/lineup.mjs approve <issue>    apply the lineup stored in that issue
//
// Rules: apps already at Apple or live keep the first slots, in their approved
// order. Every other slot goes to the highest severity score (scripts/severity.mjs),
// whether or not it is built yet. `propose` needs the miner export (Mini only);
// `approve` needs only GitHub, so it runs from .github/workflows/lineup.yml when
// the owner comments "approve" on the review issue.
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';

const REPO = 'pauljump/openappco';
const SLOTS = 10;
const CONFIG = new URL('../apps.config.json', import.meta.url);
const config = JSON.parse(readFileSync(CONFIG, 'utf8'));
const gh = (...args) => execFileSync(process.env.GH_BIN || 'gh', args, { encoding: 'utf8' });
const json = (...args) => JSON.parse(gh(...args));
const slugify = s => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const MARK = /<!-- lineup-json\n([\s\S]*?)\n-->/;

function appIssues() {
  return json('issue', 'list', '--repo', REPO, '--label', 'app', '--state', 'open', '--limit', '200', '--json', 'number,title,labels');
}
const statusOf = issue => issue?.labels.map(l => l.name).find(n => n.startsWith('status:')) || null;

async function propose(publish) {
  const { rank } = await import('./severity.mjs');
  const ranked = rank().filter(r => r.id !== 'open-piano'); // export stub for the hand-built pilot
  const issues = appIssues();
  const issueByTitle = new Map(issues.map(i => [i.title, i]));
  const appByOpp = new Map(config.apps.map(a => [a.opportunity, a]));
  const approvedSlot = new Map(config.lineup.map(e => [e.opportunity, e.slot]));

  const entry = (oppId, r) => {
    const app = appByOpp.get(oppId);
    const [name, tagline] = app ? [app.name, app.tagline] : config.names[oppId] || [r?.title, ''];
    const issue = issueByTitle.get(name);
    return { opportunity: oppId, name, slug: app?.slug || slugify(name), tagline, issue: issue?.number ?? null,
      status: statusOf(issue), score: r?.score ?? null, counts: r?.counts ?? null, complaints: r?.complaints ?? null,
      sourceApps: r?.sourceApps ?? null, worst: r?.worst ?? null, named: Boolean(app || config.names[oppId]) };
  };
  const byId = new Map(ranked.map(r => [r.id, r]));

  // 1. Pinned: anything Apple has (in review or live).
  const pinned = config.apps
    .map(a => ({ a, issue: issues.find(i => i.number === a.issue) }))
    .filter(({ issue }) => ['status:in-review', 'status:live'].includes(statusOf(issue)))
    .sort((x, y) => (approvedSlot.get(x.a.opportunity) ?? 99) - (approvedSlot.get(y.a.opportunity) ?? 99) || x.a.issue - y.a.issue)
    .map(({ a }) => ({ ...entry(a.opportunity, byId.get(a.opportunity)), pinned: true }));
  // 2. Severity order for the rest.
  const taken = new Set(pinned.map(p => p.opportunity));
  const rest = ranked.filter(r => !taken.has(r.id)).slice(0, Math.max(0, SLOTS - pinned.length)).map(r => entry(r.id, r));
  const lineup = [...pinned, ...rest].map((e, i) => ({ slot: i + 1, ...e }));

  const before = config.lineup.map(e => e.opportunity).join();
  const changed = before !== lineup.map(e => e.opportunity).join();
  const table = ['| # | App | Severity | Harm · Blocked · Ads · Other | State | Worst complaint |', '| --- | --- | --- | --- | --- | --- |',
    ...lineup.map(e => {
      const was = approvedSlot.get(e.opportunity);
      const move = was === undefined ? ' 🆕' : was !== e.slot ? ` (was #${was})` : '';
      const c = e.counts ? `${e.counts.harm} · ${e.counts.blocked} · ${e.counts.interrupted} · ${e.counts.friction}` : '—';
      const state = e.pinned ? 'At Apple' : e.issue ? (e.status || '').replace('status:', '') : 'not started';
      const q = e.worst ? `“${e.worst.quote.slice(0, 110).replace(/\|/g, '/')}${e.worst.quote.length > 110 ? '…' : ''}” — ${e.worst.app.replace(/\|/g, '/')}` : '';
      return `| ${e.slot} | **${e.name}**${move}${e.named ? '' : ' ⚠️ needs a name'} | ${e.score ?? '—'} | ${c} | ${state} | ${q} |`;
    })].join('\n');
  console.log(table);
  console.log(changed ? '\nDiffers from the approved lineup.' : '\nSame as the approved lineup.');
  if (!publish) return;

  const open = json('issue', 'list', '--repo', REPO, '--label', 'lineup-review', '--state', 'open', '--json', 'number');
  if (!changed) {
    for (const i of open) gh('issue', 'close', String(i.number), '--repo', REPO, '--comment', 'Re-ranked: same as the approved lineup. Nothing to review.');
    return;
  }
  const body = `Weekly severity re-rank of every mined app idea. Slots held by apps already at Apple stay pinned; every other slot goes to the highest severity score.

${table}

**Severity** = 8 per *harm* complaint (lost data, surprise charges, privacy, unsafe ads), 4 per *blocked* (core job paywalled or behind signup), 2 per *ads/nag*, 1 per other bug. Rubric: \`scripts/severity.mjs\`.

Comment **approve** to make this the lineup. Approval updates openappco.com and opens a tracking issue for each new app. To change it instead, reply with what you want and ask Claude to apply it.

<!-- lineup-json
${JSON.stringify(lineup.map(({ slot, opportunity, name, slug, tagline, score, counts, complaints, sourceApps, worst }) => ({ slot, opportunity, name, slug, tagline, score, counts, complaints, sourceApps, worst })))}
-->`;
  const title = `Lineup review: ${new Date().toISOString().slice(0, 10)}`;
  if (open.length) gh('issue', 'edit', String(open[0].number), '--repo', REPO, '--title', title, '--body', body);
  else gh('issue', 'create', '--repo', REPO, '--title', title, '--label', 'lineup-review', '--body', body);
}

function approve(number) {
  const issue = json('issue', 'view', String(number), '--repo', REPO, '--json', 'body,labels');
  if (!issue.labels.some(l => l.name === 'lineup-review')) throw new Error(`#${number} is not a lineup review`);
  const lineup = JSON.parse(issue.body.match(MARK)[1]);
  const issues = appIssues();
  for (const e of lineup) {
    let existing = issues.find(i => i.title === e.name);
    if (!existing) {
      const c = e.counts;
      const body = `Next: Write the brief, then build.\n\n${e.tagline}\n\nLineup slot #${e.slot}. Severity ${e.score}: ${c.harm} harm, ${c.blocked} blocked, ${c.interrupted} ads/nags, ${c.friction} other, across ${e.sourceApps} incumbent apps.\n\nWorst complaint: “${e.worst.quote}” — [${e.worst.app}](${e.worst.url})\n\n- [ ] Brief\n- [ ] Build\n- [ ] Device QA\n- [ ] Submit to Apple\n- [ ] Verify public availability`;
      const url = gh('issue', 'create', '--repo', REPO, '--title', e.name, '--label', 'app', '--label', 'status:queued', '--body', body).trim();
      existing = { number: Number(url.split('/').pop()) };
    }
    e.issue = existing.number;
  }
  config.lineup = lineup.map(({ slot, opportunity, name, slug, issue, tagline, score, counts, complaints, sourceApps, worst }) =>
    ({ slot, opportunity, name, slug, issue, tagline, score, counts, complaints, sourceApps, worst }));
  writeFileSync(CONFIG, JSON.stringify(config, null, 2) + '\n');
  gh('issue', 'close', String(number), '--repo', REPO, '--comment', `Approved. Lineup #1–#${lineup.length} is live on https://openappco.com.`);
  console.log(`Approved ${lineup.length} slots`);
}

const [cmd, arg] = process.argv.slice(2);
if (cmd === 'propose') await propose(process.argv.includes('--publish'));
else if (cmd === 'approve' && arg) approve(arg);
else { console.error('usage: lineup.mjs propose [--publish] | approve <issue>'); process.exit(2); }
