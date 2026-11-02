/* Empty release timeline; no private proposals, storage or provider connection. */
const filters = document.querySelectorAll('[data-milestone-filter]');
const labels = {all: 'All projects', mining: 'Mining', trading: 'Trading', fitness: 'Fitness'};
filters.forEach(button => button.addEventListener('click', () => {
  const selected = button.dataset.milestoneFilter;
  filters.forEach(other => other.setAttribute('aria-pressed', String(other === button)));
  document.querySelector('#milestone-count').textContent = '0 published milestones';
  document.querySelector('#milestone-empty-message').textContent = selected === 'all'
    ? 'Approved project announcements will appear here after review and publication.'
    : `No published ${labels[selected]} milestones yet. Choose another project or follow its RSS feed.`;
}));
