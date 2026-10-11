#!/usr/bin/env node
import { existsSync, readFileSync } from 'node:fs';
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
  for (const shot of page.screenshots || []) {
    const path = shot.src.replace(/^\.\.\//, 'docs/');
    if (!existsSync(resolve(root, path))) failures.push(`${page.slug}: missing ${path}`);
  }
  if (page.video) {
    const path = page.video.src.replace(/^\.\.\//, 'docs/');
    if (!existsSync(resolve(root, path))) failures.push(`${page.slug}: missing ${path}`);
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
