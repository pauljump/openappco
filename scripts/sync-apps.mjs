import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
const issues = JSON.parse(execFileSync('gh', ['issue', 'list', '--repo', 'pauljump/openappco', '--label', 'app', '--state', 'open', '--limit', '200', '--json', 'title,url,body,labels'], { encoding: 'utf8' }));
const statuses = { 'status:building': 'Building', 'status:in-review': 'In review', 'status:live': 'Live' };
const clean = s => s.replaceAll('|', '\\|').replace(/[\r\n]/g, ' ');
const rows = issues.sort((a,b) => a.title.localeCompare(b.title)).map(i => {
  const labels = i.labels.map(l => l.name).filter(l => statuses[l]);
  if (labels.length !== 1) throw new Error(`Expected one status: ${i.title}`);
  const next = i.body.match(/^Next: (.+)$/m)?.[1];
  if (!next) throw new Error(`Missing Next line: ${i.title}`);
  return `| [${clean(i.title)}](${i.url}) | ${statuses[labels[0]]} | ${clean(next)} |`;
});
if (!rows.length) throw new Error('No app issues found');
const path = new URL('../README.md', import.meta.url);
const source = readFileSync(path, 'utf8');
const table = ['<!-- apps:start -->', '| App | Status | Next |', '| --- | --- | --- |', ...rows, '<!-- apps:end -->'].join('\n');
writeFileSync(path, source.replace(/<!-- apps:start -->[\s\S]*?<!-- apps:end -->/, table));
console.log(`Updated ${rows.length} apps`);
