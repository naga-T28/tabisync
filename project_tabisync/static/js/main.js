document.addEventListener("DOMContentLoaded", function () {
    let dateIndex = 1;
    let memoIndex = 1;
    let itemIndex = 1;
  
    const datesContainer = document.getElementById("dates-container");
    const memosContainer = document.getElementById("memos-container");
    const itemsContainer = document.getElementById("items-container");
    const addDateBtn = document.getElementById("add-date-btn");
  
    // 「日付を追加」ボタン
    addDateBtn.addEventListener("click", function () {
      const html = `
        <div class="date-block" data-date-index="${dateIndex}">
          <div class="input-date">
            <div class="input-date-delete">
              <p class="input-day-number input-date-delete-number">DAY${dateIndex+1}</p>
              <button type="button" class="delete-btn input-date-delete-btn"><i class="fa-solid fa-xmark"></i> 削除</button>
            </div>
            <div class="input-date-flex">
                <label class="input-date-label">日付：</label>
                <input class="date-input-in" type="date" name="dates[${dateIndex}][date]" required>
            </div>
          </div>
          <div class="schedules-container">
            <div class="schedules-container-wrapper">
              <div class="schedule-block" data-schedule-index="0">
                <div class="input-start-end-time">
                  <label class="input-time-label">開始時刻：</label>
                  <input type="time" class="time-input" name="dates[${dateIndex}][schedules][0][start_time]" required>
                </div>
                <div class="input-start-end-time">
                  <label class="input-time-label">終了時刻：</label>
                  <input type="time" class="time-input" name="dates[${dateIndex}][schedules][0][end_time]" required>
                </div>
                <input class="input-title" type="text" name="dates[${dateIndex}][schedules][0][title]" placeholder="タイトル (例：首里城で遊ぶ)">
                <textarea class="input-description" name="dates[${dateIndex}][schedules][0][description]" placeholder="詳細 (例：公園内の龍潭を見る)"></textarea>
                <input class="location-input" type="text" name="dates[${dateIndex}][schedules][0][location]" placeholder="場所名 (例：首里城公園)">
                <input class="location-input" type="url" name="dates[${dateIndex}][schedules][0][location_url]" placeholder="位置情報URL (例：https://maps.app.goo.gl/yJqUXTNRwRkWvcKP6)">
                <button type="button" class="delete-btn delete-btn-under"><i class="fa-solid fa-trash-can"></i> この予定を削除</button>
              </div>
            </div>
            <button type="button" class="add-schedule-btn" data-date-index="${dateIndex}"><i class="fa-solid fa-circle-plus"></i> 予定を追加</button>
          </div>
        </div>
      `;
      datesContainer.insertAdjacentHTML("beforeend", html);
      datesContainer.appendChild(addDateBtn);
      dateIndex++;
    });
  
    // イベント委任：スケジュール追加・削除・日付削除
    datesContainer.addEventListener("click", function (e) {
      if (e.target.classList.contains("add-schedule-btn")) {
        const dateIdx = e.target.getAttribute("data-date-index");
        const dateBlock = e.target.closest(".date-block");
        const wrapper = dateBlock.querySelector(".schedules-container-wrapper");
  
        // スケジュールのインデックスを計算
        const currentSchedules = wrapper.querySelectorAll(".schedule-block");
        const scheduleIdx = currentSchedules.length;
  
        const html = `
          <div class="schedule-block schedule-block-next" data-schedule-index="${scheduleIdx}">
            <p class="next-arrow"><i class="fa-solid fa-angles-down"></i></p>
            <div class="input-start-end-time">
              <label class="input-time-label">開始時刻：</label>
              <input type="time" class="time-input" name="dates[${dateIdx}][schedules][${scheduleIdx}][start_time]" required>
            </div>
            <div class="input-start-end-time">
              <label class="input-time-label">終了時刻：</label>
              <input type="time" class="time-input" name="dates[${dateIdx}][schedules][${scheduleIdx}][end_time]" required>
            </div>
            <input class="input-title" type="text" name="dates[${dateIdx}][schedules][${scheduleIdx}][title]" placeholder="タイトル (例：首里城で遊ぶ)">
            <textarea class="input-description" name="dates[${dateIdx}][schedules][${scheduleIdx}][description]" placeholder="詳細 (例：公園内の龍潭を見る)"></textarea>
            <input class="location-input" type="text" name="dates[${dateIdx}][schedules][${scheduleIdx}][location]" placeholder="場所名 (例：首里城公園)">
            <input class="location-input" type="url" name="dates[${dateIdx}][schedules][${scheduleIdx}][location_url]" placeholder="位置情報URL (例：https://maps.app.goo.gl/yJqUXTNRwRkWvcKP6)">
            <button type="button" class="delete-btn delete-btn-under"><i class="fa-solid fa-trash-can"></i> この予定を削除</button>
          </div>
        `;
        wrapper.insertAdjacentHTML("beforeend", html);
      }
  
      // 削除ボタン処理
      if (e.target.classList.contains("delete-btn")) {
        const scheduleBlock = e.target.closest(".schedule-block");
        const dateBlock = e.target.closest(".date-block");
  
        if (scheduleBlock && !e.target.closest(".schedules-container").nextElementSibling?.classList?.contains("delete-btn")) {
          scheduleBlock.remove();
        } else if (dateBlock) {
          dateBlock.remove();
        }
      }
    });
  
// 「メモを追加」ボタン
document.getElementById("add-memo-btn").addEventListener("click", function () {
  const html = `
    <div class="memo-block">
      <p class="memo-title-next">メモ${memoIndex + 1}</p>
      <div class="memo-bloc-wrapper">
        <input class="input-title" type="text" name="memos[${memoIndex}][title]" placeholder="メモタイトル">
        <textarea class="input-description" name="memos[${memoIndex}][content]" placeholder="メモ詳細"></textarea>
        <button type="button" class="delete-btn delete-btn-under"><i class="fa-solid fa-trash-can"></i> このメモを削除</button>
      </div>
    </div>
  `;
  const memosContainer = document.getElementById("memos-container");
  memosContainer.insertAdjacentHTML("beforeend", html);

  // ボタンを一番下に移動
  memosContainer.appendChild(this);

  memoIndex++;
});

// 「リストを追加」ボタン
document.getElementById("add-item-btn").addEventListener("click", function () {
  const html = `
    <div class="item-block">
      <p class="memo-title-next">リスト${itemIndex + 1}</p>
      <div class="memo-bloc-wrapper">
        <input class="input-title" type="text" name="items[${itemIndex}][title]" placeholder="持ち物タイトル">
        <textarea class="input-description" name="items[${itemIndex}][detail]" placeholder="詳細"></textarea>
      <button type="button" class="delete-btn delete-btn-under"><i class="fa-solid fa-trash-can"></i> このリストを削除</button>
      </div>
    </div>
  `;
  const itemsContainer = document.getElementById("items-container");
  itemsContainer.insertAdjacentHTML("beforeend", html);

  // ボタンを一番下に移動
  itemsContainer.appendChild(this);

  itemIndex++;
});

  
    // メモ・持ち物削除ボタン
    [memosContainer, itemsContainer].forEach(container => {
      container.addEventListener("click", function (e) {
        if (e.target.classList.contains("delete-btn")) {
          const block = e.target.closest(".memo-block, .item-block");
          if (block) {
            block.remove();
          }
        }
      });
    });
  });
  