const btn = document.getElementById('btn08');
const nav = document.querySelector('.header-nav-wrapper');

btn.addEventListener('click', () => {
  btn.classList.toggle('active');
  nav.classList.toggle('active');
});

document.addEventListener("DOMContentLoaded", function () {
    const header = document.querySelector('.page-header');
    const mainVisual = document.querySelector('.main-visual');

    function updateHeaderTransparency() {
        const mainVisualBottom = mainVisual.getBoundingClientRect().bottom;

        if (mainVisualBottom > 60) {
            header.classList.add('transparent');
        } else {
            header.classList.remove('transparent');
        }
    }

    updateHeaderTransparency();
    window.addEventListener('scroll', updateHeaderTransparency);
});

document.addEventListener('DOMContentLoaded', function() {
    let formCount = document.querySelectorAll('#schedules .schedule-form').length;
  
    document.getElementById('add-schedule').addEventListener('click', function() {
      const schedules = document.getElementById('schedules');
      const lastForm = schedules.querySelector('.schedule-form:last-of-type');
      const newForm = lastForm.cloneNode(true);
  
      const regex = new RegExp(`form-(\\d+)-`, 'g');
      newForm.innerHTML = newForm.innerHTML.replace(regex, `form-${formCount}-`);
  
      // 入力値クリア
      const inputs = newForm.querySelectorAll('input, textarea');
      inputs.forEach(input => {
        if(input.type === 'checkbox') {
          input.checked = false;
        } else {
          input.value = '';
        }
      });
  
      schedules.appendChild(newForm);
  
      formCount++;
      document.getElementById('id_form-TOTAL_FORMS').value = formCount;
  
      // 削除ボタンを表示
      const removeBtn = newForm.querySelector('.remove-schedule');
      if (removeBtn) {
        removeBtn.style.display = 'inline';
      }
    });
  
    document.getElementById('schedules').addEventListener('click', function(event) {
      if (event.target.classList.contains('remove-schedule')) {
        event.target.closest('.schedule-form').remove();
        formCount--;
        document.getElementById('id_form-TOTAL_FORMS').value = formCount;
      }
    });
  });
  
// main.js（またはテンプレート内）
flatpickr("input[type='date']", {
  dateFormat: "Y-m-d",
  locale: "ja"
});

flatpickr("input[type='time']", {
  enableTime: true,
  noCalendar: true,
  dateFormat: "H:i",
  time_24hr: true,
  locale: "ja"
});
