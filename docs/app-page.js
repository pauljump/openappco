(() => {
  const root = document.querySelector('[data-app-slug]');
  const slug = root?.dataset.appSlug;
  if (!slug) return;

  const labels = {
    WAITING_FOR_REVIEW: 'Waiting for Review',
    IN_REVIEW: 'In Review',
    PENDING_APPLE_RELEASE: 'Approved by Apple',
    PENDING_DEVELOPER_RELEASE: 'Approved by Apple',
    PROCESSING_FOR_APP_STORE: 'Approved by Apple',
    READY_FOR_DISTRIBUTION: 'Live on the App Store',
    READY_FOR_SALE: 'Live on the App Store',
    REJECTED: 'Changes Requested',
    METADATA_REJECTED: 'Changes Requested',
    INVALID_BINARY: 'Changes Requested'
  };

  fetch('../apps.json', { cache: 'no-store' })
    .then(response => response.ok ? response.json() : Promise.reject(new Error('status unavailable')))
    .then(data => (Array.isArray(data) ? data : data.apps || []).find(app => app.slug === slug))
    .then(app => {
      if (!app) return;
      const isLive = Boolean(app.store?.url);
      const status = isLive ? 'Live on the App Store' : (labels[app.ascState] || app.status || 'Submitted to Apple');
      document.querySelectorAll('[data-app-status]').forEach(node => { node.textContent = status; });

      const headlines = {
        'Waiting for Review': `${app.name} is waiting for Apple review.`,
        'In Review': `${app.name} is in review at Apple.`,
        'Approved by Apple': `${app.name} was approved by Apple.`,
        'Changes Requested': `${app.name} needs changes before Apple can approve it.`
      };
      const headline = document.querySelector('[data-app-headline]');
      if (headline) headline.textContent = isLive ? `${app.name} is live.` : (headlines[status] || `${app.name}: ${status}.`);

      const next = document.querySelector('[data-app-next]');
      if (next && app.next) next.textContent = app.next;
      const checked = document.querySelector('[data-status-checked]');
      if (checked && app.ascChecked) {
        const date = new Date(`${app.ascChecked}T12:00:00`);
        checked.textContent = `Status checked ${date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}.`;
      }

      const href = isLive ? app.store.url : app.issueUrl;
      const text = isLive ? 'Get the app' : 'Follow the review status';
      document.querySelectorAll('[data-primary-link]').forEach(link => {
        if (href) link.href = href;
        link.textContent = text;
      });
    })
    .catch(() => {});
})();
