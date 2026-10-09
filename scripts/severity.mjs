// Scores every verified one-star excerpt in the opportunity corpus by how badly
// the incumbent app treated the person, then ranks opportunities by total
// severity. Deterministic and free: a fixed keyword rubric, no model calls.
//
//   node scripts/severity.mjs            print the ranking
//   node scripts/severity.mjs --json     machine-readable (used by lineup.mjs)
//
// Input: OPPORTUNITIES (default: the openforx export generated from OpenX Miner).
import { readFileSync } from 'node:fs';

const SOURCE = process.env.OPPORTUNITIES || '/Users/mini-home/projects/openforx/data/opportunities.json';

// Highest matching tier wins. Points grow fast so harm outweighs annoyance.
export const TIERS = [
  { tier: 'harm', points: 8, label: 'Harm: lost data, money, privacy, or unsafe content', patterns: [
    /\b(lost|lose|losing|deleted|erased|wiped|gone)\b.{0,40}\b(data|history|entries|entry|notes|recordings?|photos?|pictures|files?|profile|progress|everything|years?|months?)/i,
    /\b(data|history|entries|recordings?|photos?|files?|notes)\b.{0,40}\b(lost|deleted|erased|wiped|gone|disappeared|behind a paywall|locked|hostage)/i,
    /\b(hostage|held my|holding my)\b/i,
    /\b(charged|charging me|auto[- ]?renew|refund|scam|stole|stealing|can'?t cancel|cannot cancel|unauthori[sz]ed|billed)\b/i,
    /\b(personal (data|info|information)|my (email|password|location|contacts)|data leak|sell(s|ing)? (my|your) data|tracking|configuration profiles?|privacy)\b/i,
    /\b(porn|porno|naked|nude|sexual|gambling|casino)\b/i,
    /\b(unmuted|blasting|blowing my ear|eardrums|full volume|loud)\b.{0,40}\bads?\b|\bads?\b.{0,40}\b(unmuted|blasting|eardrums|full volume|loud)\b/i,
  ] },
  { tier: 'blocked', points: 4, label: 'Blocked: the core job is unusable without paying or signing up', patterns: [
    /\b(can'?t|cannot|unable to|won'?t let (me|you)|doesn'?t let (me|you)|not able to)\b.{0,50}\b(use|do anything|access|open|save|export|see|view|record|scan|play|edit|print|share)\b.{0,60}\b(pay|paid|subscri|premium|pro\b|upgrade|sign ?up|account|trial)/i,
    /\b(pay|paid|subscri\w*|premium|upgrade|trial)\b.{0,40}\b(to|before|in order to)\b.{0,20}\b(use|do anything|access|open|save|export|see|view|unlock)\b/i,
    /\b(paywall(ed)?|behind a pay ?wall|locked behind|pro feature|only (works|available) (with|if)|requires? (a )?(subscription|account|sign ?up|login|payment))\b/i,
    /\b(forced?|forces|forcing|requires?|must) (you |me )?(to )?(create an account|sign ?up|log ?in|register|provide payment|enter payment)/i,
    /\b(won'?t open|doesn'?t open|crash(es|ed|ing)? (constantly|every time|on (open|launch|startup))|keeps crashing|unusable|useless now)\b/i,
    /\b(time limit|minute limit|\d+[- ]minute (limit|cap)|limited to \d+)/i,
    /\b(bought|purchased|paid for)\b.{0,60}\b(now|then|locked|subscription|again)\b/i,
    /\b(without|unless|until)\b.{0,30}\b(pay|paying|subscri\w*|premium|purchas\w*|(an |a )?account|sign(ing)? ?up|regist\w*|rat(e|ing) it)\b/i,
    /\b(buy|pay for|purchase|get|upgrade to) (the )?(premium|pro|full version|a subscription|subscription)\b/i,
    /\b(wanted|wants|asks? (you |me )?for) money\b|\bthen (you have to |I have to )?pay\b/i,
    /\bonly "?free"? (if|for)\b|\bno functionality\b|\b(only|just) \d+ (free|times|uses|scans|items|things)\b|\bthen you have to pay\b/i,
    /\b(can|could) no longer\b.{0,30}\b(save|use|export|access|open|record|print)\b/i,
    /\b(a|per) week\b|\bweekly (pricing|subscription|fee|charge)/i,
  ] },
  { tier: 'interrupted', points: 2, label: 'Interrupted: ads or upsells break the task', patterns: [
    /\bads?\b|\badds\b|\badvert|\bpop[- ]?ups?\b|\bcommercials?\b|\boverlays?\b/i,
    /\b(rate|review|rating)\b.{0,25}\b(every time|before|first)\b|\bbegs? for a rating\b/i,
    /\b(nag|nags|nagging|pester|pestering|upsell|asks? (you|me) to (pay|upgrade|subscribe))\b/i,
  ] },
];
const FRICTION = { tier: 'friction', points: 1, label: 'Friction: bugs and missing basics' };

export function classify(text) {
  for (const t of TIERS) if (t.patterns.some(p => p.test(text))) return t;
  return FRICTION;
}

export function rank() {
  const data = JSON.parse(readFileSync(SOURCE, 'utf8'));
  const opps = data.opportunities || Object.values(data).find(Array.isArray);
  return opps.map(o => {
    const counts = { harm: 0, blocked: 0, interrupted: 0, friction: 0 };
    let score = 0, worst = null;
    for (const s of o.sources) for (const e of s.evidence || []) {
      const t = classify(e.excerpt || '');
      counts[t.tier]++; score += t.points;
      if (!worst || t.points > worst.points) worst = { points: t.points, tier: t.tier, quote: e.excerpt, app: s.name, url: s.appStoreUrl };
    }
    const n = Object.values(counts).reduce((a, b) => a + b, 0);
    return { id: o.id, slug: o.slug, title: o.title, category: o.category, buildStatus: o.buildStatus,
      sourceApps: o.sourceAppCount, complaints: n, score, mean: n ? +(score / n).toFixed(2) : 0, counts,
      worst: worst && { tier: worst.tier, quote: worst.quote, app: worst.app, url: worst.url } };
  }).sort((a, b) => b.score - a.score || b.mean - a.mean || a.title.localeCompare(b.title));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const rows = rank();
  if (process.argv.includes('--json')) { console.log(JSON.stringify(rows, null, 2)); process.exit(0); }
  for (const [i, r] of rows.slice(0, Number(process.env.TOP || 40)).entries())
    console.log(`${String(i + 1).padStart(3)} ${String(r.score).padStart(4)}  harm ${r.counts.harm} · blocked ${r.counts.blocked} · ads ${r.counts.interrupted} · other ${r.counts.friction}  [${r.buildStatus}] ${r.title}`);
}
