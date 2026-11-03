/* Local milestone filtering only: no storage, provider, request or publication code. */
const filters = document.querySelectorAll('[data-milestone-filter]');
const labels = {all: 'All projects', mining: 'Mining', trading: 'Trading', fitness: 'Fitness'};
filters.forEach(button => button.addEventListener('click', () => {
  const selected = button.dataset.milestoneFilter;
  filters.forEach(other => other.setAttribute('aria-pressed', String(other === button)));
  let count = 0;
  document.querySelectorAll('#milestone-timeline .milestone').forEach(card => {
    card.hidden = selected !== 'all' && card.dataset.project !== selected;
    if (!card.hidden) count++;
  });
  document.querySelector('#milestone-count').textContent = `${count} milestone${count === 1 ? '' : 's'}`;
  document.querySelector('#milestone-empty').hidden = count !== 0;
  document.querySelectorAll('[data-milestone-detail]').forEach(section => {
    section.hidden = selected !== 'all' && section.dataset.milestoneDetail !== selected;
  });
  document.querySelector('#milestone-empty-message').textContent = selected === 'all'
    ? 'No milestones yet. Explore the current projects or follow RSS.'
    : `No ${labels[selected]} milestones yet. Choose another project or follow its RSS feed.`;
}));
