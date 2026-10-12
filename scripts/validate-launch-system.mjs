#!/usr/bin/env node
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const appConfig = JSON.parse(readFileSync(resolve(root, 'apps.config.json'), 'utf8'));
const pageConfig = JSON.parse(readFileSync(resolve(root, 'app-pages.config.json'), 'utf8'));
const configured = new Map(appConfig.apps.map(app => [app.slug, app]));
const numbers = new Set();
const failures = [];

for (const page of pageConfig.apps) {
  const meta = configured.get(page.slug);
  if (!meta) failures.push(`${page.slug}: missing from apps.config.json`);
  if (!Number.isSafeInteger(page.launchNumber) || page.launchNumber < 1) failures.push(`${page.slug}: invalid launchNumber`);
  if (numbers.has(page.launchNumber)) failures.push(`${page.slug}: duplicate launchNumber ${page.launchNumber}`);
  numbers.add(page.launchNumber);
  if (meta?.launchNumber !== page.launchNumber) failures.push(`${page.slug}: launchNumber disagrees with apps.config.json`);
  if (!page.tinyDescription) failures.push(`${page.slug}: missing tinyDescription`);
  if (!page.fixes?.length) failures.push(`${page.slug}: missing verified complaint/fix rows`);
  for (const item of page.fixes || []) {
    if (!item.quote || !item.source || !item.sourceUrl || !item.fix) failures.push(`${page.slug}: incomplete complaint/fix row`);
  }
  for (const file of [
    `docs/${page.slug}/index.html`,
    `docs/assets/apps/${page.slug}/icon.png`,
    `docs/assets/apps/${page.slug}/shot.jpg`,
    `docs/assets/apps/${page.slug}/launch-card.png`
  ]) if (!existsSync(resolve(root, file))) failures.push(`${page.slug}: missing ${file}`);
  // The homepage card shows shot.jpg whole: it must be the app's full first screenshot at
  // 414x900 (900x414 for landscape apps), never a crop or a missing image (Paul, 2026-10-12).
  const shotPath = resolve(root, `docs/assets/apps/${page.slug}/shot.jpg`);
  if (existsSync(shotPath)) {
    const size = jpegSize(readFileSync(shotPath));
    const want = meta?.landscape ? '900x414' : '414x900';
    if (!size) failures.push(`${page.slug}: shot.jpg is not a readable JPEG`);
    else if (`${size.w}x${size.h}` !== want) failures.push(`${page.slug}: shot.jpg is ${size.w}x${size.h}; needs ${want} (the whole first screenshot)`);
  }
  for (const shot of page.screenshots || []) {
    const path = shot.src.replace(/^\.\.\//, 'docs/');
    if (!existsSync(resolve(root, path))) failures.push(`${page.slug}: missing ${path}`);
  }
  if (page.video) {
    const path = page.video.src.replace(/^\.\.\//, 'docs/');
    if (!existsSync(resolve(root, path))) failures.push(`${page.slug}: missing ${path}`);
  }
}

// Public pages give support@openappco.com (forwarded) as the contact, never a personal address
// (Paul, 2026-10-12).
for (const file of readdirSync(resolve(root, 'docs'), { recursive: true })) {
  if (!/\.(html|js|json|md)$/.test(file)) continue;
  for (const email of readFileSync(resolve(root, 'docs', file), 'utf8').match(/[\w.+-]+@[\w-]+\.[\w.-]+/g) || []) {
    if (!/@openappco\.com$/i.test(email)) failures.push(`docs/${file}: non-openappco email ${email}`);
  }
}

const ordered = [...numbers].sort((a, b) => a - b);
for (let number = 1; number <= Math.max(...ordered); number += 1) {
  if (!numbers.has(number)) failures.push(`launchNumber ${number} is missing`);
}

if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log(`Validated ${pageConfig.apps.length} launch kits, numbered 1-${Math.max(...ordered)}.`);

function jpegSize(buf) {
  let i = 2;
  while (i < buf.length) {
    if (buf[i] !== 0xff) return null;
    const marker = buf[i + 1], len = buf.readUInt16BE(i + 2);
    if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker)) return { h: buf.readUInt16BE(i + 5), w: buf.readUInt16BE(i + 7) };
    i += 2 + len;
  }
  return null;
}
