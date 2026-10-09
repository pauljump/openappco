(() => {
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const REPO = 'pauljump/openappco';

  /* ---------- the piano ---------- */
  const whites = [['C', 261.63, 'a'], ['D', 293.66, 's'], ['E', 329.63, 'd'], ['F', 349.23, 'f'], ['G', 392.0, 'g'], ['A', 440.0, 'h'], ['B', 493.88, 'j'], ['C', 523.25, 'k'], ['D', 587.33, 'l'], ['E', 659.25, ';']];
  const blacks = [['C♯', 277.18, 'w', 1], ['D♯', 311.13, 'e', 2], ['F♯', 369.99, 't', 4], ['G♯', 415.3, 'y', 5], ['A♯', 466.16, 'u', 6], ['C♯', 554.37, 'o', 8], ['D♯', 622.25, 'p', 9]];
  const piano = $('#piano'), trail = $('#trail');
  let ctx, notes = 0, adShown = sessionStorage.getItem('oac-ad') === '1', blocked = false;
  const byKey = {};

  function tone(freq) {
    ctx ||= new (window.AudioContext || window.webkitAudioContext)();
    if (ctx.state === 'suspended') ctx.resume();
    const t = ctx.currentTime, out = ctx.createGain(), lp = ctx.createBiquadFilter();
    lp.type = 'lowpass'; lp.frequency.setValueAtTime(freq * 6, t); lp.frequency.exponentialRampToValueAtTime(freq * 1.5, t + 1.2);
    out.gain.setValueAtTime(0.0001, t); out.gain.exponentialRampToValueAtTime(0.32, t + 0.008); out.gain.exponentialRampToValueAtTime(0.0001, t + 1.8);
    [[1, 'triangle', 1], [2, 'sine', 0.35], [3, 'sine', 0.12]].forEach(([m, type, g]) => {
      const o = ctx.createOscillator(), og = ctx.createGain();
      o.type = type; o.frequency.value = freq * m; og.gain.value = g;
      o.connect(og).connect(lp); o.start(t); o.stop(t + 1.9);
    });
    lp.connect(out).connect(ctx.destination);
  }

  function play(el, name, freq) {
    if (blocked) return;
    tone(freq);
    el.classList.add('on'); setTimeout(() => el.classList.remove('on'), 160);
    trail.querySelector('.trail-empty')?.remove();
    const chip = document.createElement('span'); chip.textContent = name; trail.append(chip);
    while (trail.children.length > 24) trail.firstChild.remove();
    if (++notes === 6 && !adShown) setTimeout(showAd, 220);
  }

  function makeKey(cls, name, freq, key, style) {
    const el = document.createElement('button');
    el.type = 'button'; el.className = cls; el.textContent = name; el.setAttribute('aria-label', name);
    if (style) el.style.left = style;
    el.addEventListener('pointerdown', e => { e.preventDefault(); play(el, name, freq); });
    el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); play(el, name, freq); } });
    byKey[key] = () => play(el, name, freq);
    piano.append(el);
  }
  whites.forEach(([n, f, k]) => makeKey('key', n, f, k));
  blacks.forEach(([n, f, k, i]) => makeKey('bk', '', f, k, `calc(${i * 10}% - ${10 * 0.31}%)`));
  document.addEventListener('keydown', e => {
    if (e.repeat || e.metaKey || e.ctrlKey || e.altKey || /input|textarea/i.test(e.target.tagName)) return;
    const fn = byKey[e.key.toLowerCase()]; if (fn && piano.getBoundingClientRect().bottom > 0) fn();
  });

  /* ---------- the interruption ---------- */
  function showAd() {
    adShown = true; blocked = true; sessionStorage.setItem('oac-ad', '1');
    const ad = $('#ad'), close = $('#ad-close');
    ad.hidden = false; close.disabled = true;
    let n = 3; close.textContent = n;
    track('piano_ad_shown');
    const tick = setInterval(() => {
      if (--n > 0) { close.textContent = n; return; }
      clearInterval(tick); close.disabled = false; close.textContent = '✕'; close.focus();
    }, 1000);
  }
  $('#ad-close').addEventListener('click', () => { $('#ad').hidden = true; $('#reveal').hidden = false; $('#reveal-close').focus(); });
  $('#reveal-close').addEventListener('click', () => { $('#reveal').hidden = true; blocked = false; piano.querySelector('.key').focus(); });
  function track(name) { try { window.posthog?.capture(name); } catch {} }

  /* ---------- stars (likes) ---------- */
  fetch(`https://api.github.com/repos/${REPO}`, { signal: AbortSignal.timeout(6000) })
    .then(r => r.ok ? r.json() : Promise.reject())
    .then(d => { if (Number.isSafeInteger(d.stargazers_count)) document.querySelectorAll('[data-stars]').forEach(el => { el.textContent = (el.classList.contains('star-count') ? '★ ' : '') + d.stargazers_count.toLocaleString(); }); })
    .catch(() => document.querySelectorAll('[data-stars]').forEach(el => { el.textContent = '★'; }));

  /* ---------- the lineup ---------- */
  const STAGES = ['Submitted', 'In review', 'Live'];
  const stageIndex = { changes: 0, submitted: 0, review: 1, approved: 1, live: 2 };
  const stateText = {
    changes: '<b>Apple asked for changes.</b> Fixing and resubmitting.',
    submitted: '<b>Waiting for Apple review.</b> Submitted and in line.',
    review: '<b>Apple is reviewing it right now.</b>',
    approved: '<b>Approved by Apple.</b> Releasing to the App Store.',
    live: '<b>Live on the App Store.</b> Free, for everyone.'
  };
  const badge = { queued: ['Queued', ''], building: ['Building', ''], changes: ['Changes requested', 'changes'], submitted: ['At Apple', 'apple'], review: ['In review', 'apple'], approved: ['Approved', 'apple'], live: ['Live', 'live'] };

  function card(a) {
    const idx = stageIndex[a.stage] ?? 0;
    const keys = STAGES.map((_, i) => `<i class="${a.stage === 'live' && i === 2 ? 'live-k' : i < idx ? 'done' : i === idx ? (a.stage === 'live' ? 'live-k' : 'now') : ''}"></i>`).join('');
    const labels = STAGES.map((s, i) => `<span class="${i === idx ? 'cur' : ''}">${s}</span>`).join('');
    const o = a.origin;
    const [btext, bcls] = badge[a.stage] || badge.building;
    const shot = a.hasShot
      ? `<div class="shot" style="background-image:url('assets/apps/${esc(a.slug)}/shot.jpg')" role="img" aria-label="${esc(a.name)} screenshot"><span class="badge ${bcls}">${btext}</span></div>`
      : `<div class="shot empty"><span class="badge ${bcls}">${btext}</span><div>${o ? `<q>${esc(o.quote)}</q><small>one-star review of ${esc(o.source)}</small>` : ''}</div></div>`;
    const origin = o && a.hasShot ? `<div class="origin"><q>${esc(o.quote)}</q><small>Why it exists: <a href="${esc(o.url)}" rel="noopener">${esc(o.source)}</a></small></div>` : '';
    const icon = a.hasIcon ? `<img src="assets/apps/${esc(a.slug)}/icon.png" alt="" loading="lazy">` : `<span class="t-icon">${esc(a.name.replace('Open ', '')[0])}</span>`;
    const get = a.store ? `<a class="get store" href="${esc(a.store.url)}" rel="noopener">Get it free</a>` : `<a class="get" href="${esc(a.issueUrl)}" rel="noopener">Follow progress →</a>`;
    return `<article class="card${a.landscape ? ' feature' : ''}" id="${esc(a.slug)}">${shot}
      <div class="body">
        <div class="app-head">${icon}<h3>${esc(a.name)}</h3></div>
        <p class="tagline">${esc(a.tagline)}</p>
        <div class="keys" aria-hidden="true">${keys}</div><div class="keys-labels" aria-label="Stage: ${STAGES[idx]}">${labels}</div>
        <p class="state">${stateText[a.stage] || stateText.building}</p>
        ${origin}
        <div class="card-foot"><a class="like" href="${esc(a.issueUrl)}" rel="noopener" title="Like it with a 👍 on GitHub">👍 <b>${a.likes || 0}</b></a>${get}</div>
      </div></article>`;
  }

  function render(data) {
    const order = { live: 0, approved: 1, review: 2, submitted: 3, changes: 4 };
    const apps = data.apps.slice().sort((a, b) => (b.landscape ? 1 : 0) - (a.landscape ? 1 : 0) || order[a.stage] - order[b.stage] || a.name.localeCompare(b.name));
    $('#grid').innerHTML = apps.map(card).join('');
    const count = s => apps.filter(a => s.includes(a.stage)).length;
    $('#pipeline').innerHTML = [
      ['apple', count(['submitted', 'changes']), 'Submitted', 'Waiting in Apple’s line'],
      ['apple', count(['review', 'approved']), 'In review', 'Apple is looking at it'],
      ['live', count(['live']), 'Live', 'Free on the App Store']
    ].map(([c, n, l, s]) => `<div class="pipe ${c}"><b>${n}</b><span>${l}</span><small>${s}</small></div>`).join('');
    if (data.generated) $('#updated').textContent = 'Status as of ' + new Date(data.generated).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) + '.';
    const chips = apps.filter(a => a.origin).map(a => `<div class="quote-chip"><span class="stars1">★☆☆☆☆</span><q>${esc(a.origin.quote)}</q><small>${esc(a.origin.source)}</small></div>`).join('');
    $('#heard').innerHTML = chips.repeat(3);
  }

  // apps.json is rendered by the status workflow; the live GitHub read refreshes
  // 👍 counts and catches label changes between workflow runs.
  fetch('apps.json', { cache: 'no-cache' }).then(r => r.json()).then(data => {
    render(data);
    fetch(`https://api.github.com/repos/${REPO}/issues?labels=app&state=open&per_page=100`, { signal: AbortSignal.timeout(6000) })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(issues => {
        let changed = false;
        for (const i of issues) {
          const a = data.apps.find(x => x.issue === i.number); if (!a) continue;
          const likes = i.reactions?.['+1'] ?? a.likes;
          const label = i.labels.map(l => l.name).find(n => n.startsWith('status:'));
          if (likes !== a.likes) { a.likes = likes; changed = true; }
          if (label && label !== a.label && !a.store) {
            a.label = label; changed = true;
            a.stage = label === 'status:live' ? 'live' : label === 'status:in-review' ? (a.stage === 'review' || a.stage === 'approved' ? a.stage : 'submitted') : 'changes';
          }
        }
        if (changed) render(data);
      }).catch(() => {});
  }).catch(() => { $('#grid').innerHTML = '<p class="loading">The board is on <a href="https://github.com/pauljump/openappco">GitHub</a>.</p>'; });
})();
