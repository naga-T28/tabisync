const btn = document.getElementById('btn08');
const nav = document.querySelector('.header-nav-wrapper');

btn.addEventListener('click', () => {
  btn.classList.toggle('active');
  nav.classList.toggle('active');
});


