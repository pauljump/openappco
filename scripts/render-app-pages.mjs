#!/usr/bin/env node
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const appConfig = JSON.parse(readFileSync(resolve(root, 'apps.config.json'), 'utf8'));
const pageConfig = JSON.parse(readFileSync(resolve(root, 'app-pages.config.json'), 'utf8'));
const statusData = JSON.parse(readFileSync(resolve(root, 'docs/apps.json'), 'utf8'));
const statusBySlug = new Map(statusData.apps.map(app => [app.slug, app]));
const metaBySlug = new Map(appConfig.apps.map(app => [app.slug, app]));

const esc = value => String(value ?? '').replace(/[&<>"']/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[character]));

function pageLink(link, slug) {
  if (!link) return '#';
  if (/^https?:\/\//.test(link)) return link;
  return link.startsWith(`${slug}/`) ? link.slice(slug.length + 1) : `../${link}`;
}

function statusFor(page, current) {
  if (current?.store?.url) return 'Live on the App Store';
  const labels = {
    WAITING_FOR_REVIEW: 'Waiting for Review', IN_REVIEW: 'In Review',
    PENDING_APPLE_RELEASE: 'Approved by Apple', PENDING_DEVELOPER_RELEASE: 'Approved by Apple',
    PROCESSING_FOR_APP_STORE: 'Approved by Apple', READY_FOR_DISTRIBUTION: 'Live on the App Store',
    READY_FOR_SALE: 'Live on the App Store', REJECTED: 'Changes Requested',
    METADATA_REJECTED: 'Changes Requested', INVALID_BINARY: 'Changes Requested'
  };
  return labels[current?.ascState] || page.fallbackStatus || current?.status || 'Submitted to Apple';
}

function headline(name, status) {
  return ({
    'Waiting for Review': `${name} is waiting for Apple review.`,
    'In Review': `${name} is in review at Apple.`,
    'Approved by Apple': `${name} was approved by Apple.`,
    'Live on the App Store': `${name} is live.`,
    'Changes Requested': `${name} needs changes before Apple can approve it.`
  })[status] || `${name}: ${status}.`;
}

function screenshots(page) {
  if (!page.screenshots?.length) return '';
  const items = page.screenshots.map(item => `<figure><img src="${esc(item.src)}" alt="${esc(item.alt)}" loading="lazy"><figcaption>${esc(item.caption)}</figcaption></figure>`).join('\n');
  return `<section aria-labelledby="screenshots">
  <p class="section-kicker">The actual app</p>
  <h2 id="screenshots">${page.screenshots.length === 1 ? 'See the app.' : `${page.screenshots.length} screens. No sales pitch.`}</h2>
  <div class="screenshot-grid count-${Math.min(page.screenshots.length, 3)}">${items}</div>
</section>`;
}

function video(page) {
  if (!page.video) return '';
  return `<section aria-labelledby="video">
  <p class="section-kicker">${esc(page.video.label)}</p>
  <h2 id="video">It works on a real iPhone.</h2>
  <p>${esc(page.video.description)}</p>
  <div class="video-frame"><video controls muted playsinline preload="metadata" poster="${esc(page.video.poster)}"><source src="${esc(page.video.src)}" type="video/mp4">Your browser does not support the demo video.</video></div>
</section>`;
}

function fixes(page, name) {
  const items = page.fixes.map(item => `<article>
  <blockquote>“${esc(item.quote)}”</blockquote>
  <p><a href="${esc(item.sourceUrl)}" rel="noopener">${esc(item.source)} on the App Store</a></p>
  <h3>What ${esc(name)} does instead</h3>
  <p>${esc(item.fix)}</p>
</article>`).join('\n');
  // One plain line on where the complaints came from; the full audit stays in private research.
  const source = page.reviewLine ? `\n<p class="lede">${esc(page.reviewLine)}</p>` : '';
  return `<section aria-labelledby="complaints">
<p class="section-kicker">Why this app exists</p>
<h2 id="complaints">What people hated. What we fixed for free.</h2>${source}
${items}
</section>`;
}

function render(page) {
  const meta = metaBySlug.get(page.slug);
  if (!meta) throw new Error(`Unknown app slug: ${page.slug}`);
  if (meta.launchNumber !== page.launchNumber) throw new Error(`Launch number mismatch for ${page.slug}`);
  const current = statusBySlug.get(page.slug);
  const status = statusFor(page, current);
  const isLive = Boolean(current?.store?.url);
  const issueUrl = current?.issueUrl || `https://github.com/pauljump/openappco/issues/${meta.issue}`;
  const primaryUrl = isLive ? current.store.url : issueUrl;
  const primaryText = isLive ? 'Get it free' : 'Follow the review status';
  const checked = current?.ascChecked || page.submittedDate;
  const next = current?.next || page.fallbackNext;
  const support = pageLink(meta.links?.support, page.slug);
  const privacy = pageLink(meta.links?.privacy, page.slug);
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(meta.name)} — ${esc(status)}</title>
<meta name="description" content="${esc(meta.name)}: ${esc(status)}. See the app and the App Store feedback we addressed for free.">
<meta property="og:title" content="${esc(meta.name)} — Open AppCo app #${page.launchNumber}">
<meta property="og:description" content="${esc(page.tinyDescription)}">
<meta property="og:image" content="https://openappco.com/assets/apps/${page.slug}/launch-card.png">
<meta property="og:url" content="https://openappco.com/${page.slug}/">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="../styles.css">
<script src="https://pulse.polyfeeds.dev/_pulse/posthog.js" defer></script>
</head>
<body><main class="app-page" data-app-slug="${page.slug}">
<nav><a class="brand" href="../">Open AppCo</a><a data-primary-link href="${esc(primaryUrl)}">${primaryText}</a><a href="${esc(support)}">Support</a><a href="${esc(privacy)}">Privacy</a></nav>
<header class="app-hero">
  <p class="eyebrow">Open AppCo app #${page.launchNumber}</p>
  <div class="status-line" aria-live="polite"><span class="status-dot" aria-hidden="true"></span><strong data-app-status>${esc(status)}</strong></div>
  <h1 data-app-headline>${esc(headline(meta.name, status))}</h1>
  <p class="lede">${esc(page.tinyDescription)}</p>
  <p data-app-next>${esc(next)}</p>
  <p class="status-meta" data-status-checked>Status checked ${esc(checked)}.</p>
  <p><a class="cta" data-primary-link href="${esc(primaryUrl)}">${primaryText}</a></p>
</header>
${screenshots(page)}
${video(page)}
${fixes(page, meta.name)}
<p><a class="cta" data-primary-link href="${esc(primaryUrl)}">${primaryText}</a></p>
<footer>Open AppCo · Everyday apps. Free for everyone.</footer>
</main>
<script src="../app-page.js" defer></script>
</body>
</html>\n`;
}

const postSlug = process.argv[process.argv.indexOf('--post') + 1];
if (process.argv.includes('--post')) {
  const page = pageConfig.apps.find(app => app.slug === postSlug);
  const meta = metaBySlug.get(postSlug);
  if (!page || !meta) throw new Error(`Unknown --post slug: ${postSlug}`);
  process.stdout.write(`Open AppCo app #${page.launchNumber}: ${meta.name}.\n\nI sent it to Apple for review today.\n\n${page.tinyDescription}\n\nFree. No ads. No account. No tracking. Nothing to unlock.\n\nhttps://openappco.com/${page.slug}/\n`);
  process.exit(0);
}

for (const page of pageConfig.apps) {
  const output = resolve(root, 'docs', page.slug, 'index.html');
  mkdirSync(dirname(output), { recursive: true });
  writeFileSync(output, render(page));
}
console.log(`Rendered ${pageConfig.apps.length} app pages.`);
