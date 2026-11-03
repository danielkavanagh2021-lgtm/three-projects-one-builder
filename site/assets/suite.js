/* Local roadmap filtering only. Future plans never become milestone or RSS items. */
const roadmapFilters = document.querySelectorAll('[data-roadmap-filter]');
roadmapFilters.forEach(button => button.addEventListener('click', () => {
  const selected = button.dataset.roadmapFilter;
  roadmapFilters.forEach(other => other.setAttribute('aria-pressed', String(other === button)));
  let count = 0;
  document.querySelectorAll('[data-roadmap-projects]').forEach(card => {
    card.hidden = selected !== 'all' && !card.dataset.roadmapProjects.split(' ').includes(selected);
    if (!card.hidden) count++;
  });
  document.querySelector('#roadmap-count').textContent = `${count} future-development item${count === 1 ? '' : 's'}`;
}));
