/* Local presentation only. No analytics, storage, network APIs or app connections. */
const toggle = document.querySelector('.menu-toggle');
const nav = document.querySelector('#primary-nav');
if (toggle && nav) {
  toggle.hidden = false;
  const closeMenu = () => { toggle.setAttribute('aria-expanded', 'false'); nav.classList.remove('is-open'); };
  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') !== 'true';
    toggle.setAttribute('aria-expanded', String(open)); nav.classList.toggle('is-open', open);
  });
  nav.addEventListener('click', (event) => { if (event.target.closest('a')) closeMenu(); });
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && nav.classList.contains('is-open')) { closeMenu(); toggle.focus(); } });
}

const viewer = document.querySelector('#image-viewer');
let gallery = [], imageIndex = 0, opener = null;
if (viewer && typeof viewer.showModal === 'function') {
  const image = viewer.querySelector('img');
  const caption = viewer.querySelector('#viewer-caption');
  const position = viewer.querySelector('#viewer-position');
  const show = (index) => {
    imageIndex = (index + gallery.length) % gallery.length;
    const link = gallery[imageIndex]; image.src = link.href;
    image.alt = link.querySelector('img').alt;
    caption.textContent = link.dataset.caption || image.alt;
    position.textContent = `${imageIndex + 1} / ${gallery.length}`;
    viewer.querySelector('.original-link').href = link.href;
  };
  document.querySelectorAll('a[data-lightbox]').forEach((link) => {
    link.addEventListener('click', (event) => {
      event.preventDefault(); opener = link;
      gallery = Array.from(document.querySelectorAll(`a[data-lightbox="${link.dataset.lightbox}"]`));
      show(gallery.indexOf(link)); viewer.showModal(); document.body.classList.add('viewer-open');
    });
  });
  viewer.querySelector('.viewer-close').addEventListener('click', () => viewer.close());
  viewer.querySelector('.viewer-prev').addEventListener('click', () => show(imageIndex - 1));
  viewer.querySelector('.viewer-next').addEventListener('click', () => show(imageIndex + 1));
  viewer.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowLeft') { event.preventDefault(); show(imageIndex - 1); }
    if (event.key === 'ArrowRight') { event.preventDefault(); show(imageIndex + 1); }
  });
  viewer.addEventListener('click', (event) => { if (event.target === viewer) viewer.close(); });
  viewer.addEventListener('close', () => { document.body.classList.remove('viewer-open'); opener?.focus(); });
}

// Subtle entrance effects are decorative; all content remains visible without JS.
if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches && 'IntersectionObserver' in window) {
  const observer = new IntersectionObserver((entries, instance) => {
    entries.forEach((entry) => { if (entry.isIntersecting) { entry.target.classList.add('arrived'); instance.unobserve(entry.target); } });
  }, { threshold: 0.08 });
  document.querySelectorAll('.reveal').forEach((element) => observer.observe(element));
}
