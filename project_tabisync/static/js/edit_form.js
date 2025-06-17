// static/js/edit_form.js
document.addEventListener("DOMContentLoaded", function () {
  let dateIndex = document.querySelectorAll(".date-block").length;
  let memoIndex = document.querySelectorAll(".memo-block").length;
  let itemIndex = document.querySelectorAll(".item-block").length;

  const datesContainer = document.getElementById("dates-container");
  const memosContainer = document.getElementById("memos-container");
  const itemsContainer = document.getElementById("items-container");

  // 日付追加
  document.getElementById("add-date-btn").addEventListener("click", function () {
    const html = `
      <div class="date-block" data-date-index="${dateIndex}">
        <input type="date" name="dates[${dateIndex}][date]" required>
        <div class="schedules-container-wrapper">
          <div class="schedule-block" data-schedule-index="0">
            <input type="time" name="dates[${dateIndex}][schedules][0][start_time]" required>
            <input type="time" name="dates[${dateIndex}][schedules][0][end_time]">
            <input type="text" name="dates[${dateIndex}][schedules][0][title]" placeholder="タイトル">
            <textarea name="dates[${dateIndex}][schedules][0][description]" placeholder="詳細"></textarea>
            <input type="text" name="dates[${dateIndex}][schedules][0][location]" placeholder="場所名">
            <input type="url" name="dates[${dateIndex}][schedules][0][location_url]" placeholder="URL">
            <button type="button" class="delete-btn">この予定を削除</button>
          </div>
        </div>
        <button type="button" class="add-schedule-btn" data-date-index="${dateIndex}">予定を追加</button>
      </div>`;
    datesContainer.insertAdjacentHTML("beforeend", html);
    dateIndex++;
  });

  // スケジュール追加／削除
  datesContainer.addEventListener("click", function (e) {
    if (e.target.classList.contains("add-schedule-btn")) {
      const dateIdx = e.target.dataset.dateIndex;
      const wrapper = e.target.closest(".date-block").querySelector(".schedules-container-wrapper");
      const scheduleIdx = wrapper.querySelectorAll(".schedule-block").length;
      const html = `
        <div class="schedule-block" data-schedule-index="${scheduleIdx}">
          <input type="time" name="dates[${dateIdx}][schedules][${scheduleIdx}][start_time]" required>
          <input type="time" name="dates[${dateIdx}][schedules][${scheduleIdx}][end_time]">
          <input type="text" name="dates[${dateIdx}][schedules][${scheduleIdx}][title]" placeholder="タイトル">
          <textarea name="dates[${dateIdx}][schedules][${scheduleIdx}][description]" placeholder="詳細"></textarea>
          <input type="text" name="dates[${dateIdx}][schedules][${scheduleIdx}][location]" placeholder="場所名">
          <input type="url" name="dates[${dateIdx}][schedules][${scheduleIdx}][location_url]" placeholder="URL">
          <button type="button" class="delete-btn">この予定を削除</button>
        </div>`;
      wrapper.insertAdjacentHTML("beforeend", html);
    }

    if (e.target.classList.contains("delete-btn")) {
      const schedule = e.target.closest(".schedule-block");
      const dateBlock = e.target.closest(".date-block");
      if (schedule) schedule.remove();
      else if (dateBlock) dateBlock.remove();
    }
  });

  // メモ追加
  document.getElementById("add-memo-btn").addEventListener("click", function () {
    const html = `
      <div class="memo-block">
        <input type="text" name="memos[${memoIndex}][title]" placeholder="メモタイトル">
        <textarea name="memos[${memoIndex}][content]" placeholder="内容"></textarea>
        <button type="button" class="delete-btn">このメモを削除</button>
      </div>`;
    memosContainer.insertAdjacentHTML("beforeend", html);
    memoIndex++;
  });

  // 持ち物追加
  document.getElementById("add-item-btn").addEventListener("click", function () {
    const html = `
      <div class="item-block">
        <input type="text" name="items[${itemIndex}][title]" placeholder="持ち物">
        <textarea name="items[${itemIndex}][detail]" placeholder="詳細"></textarea>
        <button type="button" class="delete-btn">このリストを削除</button>
      </div>`;
    itemsContainer.insertAdjacentHTML("beforeend", html);
    itemIndex++;
  });

  // メモ・持ち物 削除
  [memosContainer, itemsContainer].forEach(container => {
    container.addEventListener("click", function (e) {
      if (e.target.classList.contains("delete-btn")) {
        e.target.closest(".memo-block, .item-block")?.remove();
      }
    });
  });
});
