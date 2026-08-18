const btn = document.getElementById('btn08');
const nav = document.querySelector('.header-nav-wrapper');
const header = document.querySelector('.page-header');
const backToTop = document.getElementById('back-to-top');
const BACK_TO_TOP_THRESHOLD = 400;

function syncHeaderBackground() {
  if (!header) return;
  header.classList.toggle('is-scrolled', window.scrollY >= 80);
}

function syncBackToTopVisibility() {
  if (!backToTop) return;
  backToTop.classList.toggle('is-visible', window.scrollY >= BACK_TO_TOP_THRESHOLD);
}

syncHeaderBackground();
syncBackToTopVisibility();
window.addEventListener('scroll', syncHeaderBackground, { passive: true });
window.addEventListener('scroll', syncBackToTopVisibility, { passive: true });

if (backToTop) {
  backToTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

if (btn && nav) {
  btn.addEventListener('click', () => {
    btn.classList.toggle('active');
    nav.classList.toggle('active');
  });
}
