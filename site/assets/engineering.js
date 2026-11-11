/* Local filters plus an explicitly requested YouTube frame. No analytics or storage. */
const projectFilters = document.querySelectorAll('[data-project-filter]');
projectFilters.forEach(button => button.addEventListener('click', () => {
  const selected = button.dataset.projectFilter;
  projectFilters.forEach(other => other.setAttribute('aria-pressed', String(other === button)));
  let shown = 0;
  document.querySelectorAll('[data-project-category]').forEach(card => {
    card.hidden = selected !== 'all' && card.dataset.projectCategory !== selected;
    if (!card.hidden) shown++;
  });
  document.querySelector('#project-total').textContent = `${shown} project areas shown`;
}));

const videoButton = document.querySelector('#load-nissan-video');
if (videoButton) videoButton.addEventListener('click', () => {
  const frame = document.createElement('iframe');
  frame.src = 'https://www.youtube-nocookie.com/embed/VVGeANYMzQs?playsinline=1&rel=0';
  frame.title = 'My First Digital Twin Ever — historical project from previous employment';
  frame.referrerPolicy = 'strict-origin-when-cross-origin';
  frame.allow = 'encrypted-media; picture-in-picture; fullscreen';
  frame.allowFullscreen = true;
  document.querySelector('#nissan-video-player').replaceChildren(frame);
  document.querySelector('#video-status').textContent = 'YouTube player loaded. Press Play in the player to start. If unavailable, use the direct link below.';
  frame.focus();
}, {once: true});
