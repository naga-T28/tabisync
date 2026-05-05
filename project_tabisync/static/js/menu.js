const btn = document.getElementById('btn08');
const nav = document.querySelector('.header-nav-wrapper');
const header = document.querySelector('.page-header');

function syncHeaderBackground() {
  if (!header) return;
  header.classList.toggle('is-scrolled', window.scrollY >= 80);
}

syncHeaderBackground();
window.addEventListener('scroll', syncHeaderBackground, { passive: true });

if (btn && nav) {
  btn.addEventListener('click', () => {
    btn.classList.toggle('active');
    nav.classList.toggle('active');
  });
}
