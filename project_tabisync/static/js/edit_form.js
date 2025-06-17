// edit_form.js（HTML構造・class名は維持）
document.addEventListener("DOMContentLoaded", function () {
    let dateIndex = document.querySelectorAll('.date-block').length;
    let memoIndex = document.querySelectorAll('.memo-block').length;
    let itemIndex = document.querySelectorAll('.item-block').length;

    const datesContainer = document.getElementById("dates-container");
    const memosContainer = document.getElementById("memos-container");
    const itemsContainer = document.getElementById("items-container");
    const addDateBtn = document.getElementById("add-date-btn");

    addDateBtn.addEventListener("click", function () {
        const html = `
        <div class="date-block" data-date-index="${dateIndex}">
            <div class="input-date">
                <label class="input-date-label">日付：</label>
                <input class="date-input-in" type="date" name="dates[${dateIndex}][date]" required>
            </div>
            <div class="schedules-container">
                <div class="schedules-container-wrapper">
                    <div class="schedule-block">
                        <input type="time" class="time-input" name="dates[${dateIndex}][schedules][0][start_time]">
                        <input type="time" class="time-input" name="dates[${dateIndex}][schedules][0][end_time]">
                        <input class="input-title" type="text" name="dates[${dateIndex}][schedules][0][title]">
                        <textarea class="input-description" name="dates[${dateIndex}][schedules][0][description]"></textarea>
                        <input class="location-input" type="text" name="dates[${dateIndex}][schedules][0][location]">
                        <input class="location-input" type="url" name="dates[${dateIndex}][schedules][0][location_url]">
                        <button type="button" class="delete-btn delete-btn-under"><i class="fa-solid fa-trash-can"></i> この予定を削除</button>
                    </div>
                </div>
                <button type="button" class="add-schedule-btn" data-date-index="${dateIndex}">予定を追加</button>
            </div>
        </div>
        `;
        datesContainer.insertAdjacentHTML("beforeend", html);
        dateIndex++;
    });

    datesContainer.addEventListener("click", function (e) {
        if (e.target.closest(".add-schedule-btn")) {
            const btn = e.target.closest(".add-schedule-btn");
            const idx = btn.dataset.dateIndex;
            const wrapper = btn.parentElement.querySelector(".schedules-container-wrapper");
            const scheduleCount = wrapper.querySelectorAll(".schedule-block").length;

            const html = `
            <div class="schedule-block">
                <input type="time" class="time-input" name="dates[${idx}][schedules][${scheduleCount}][start_time]">
                <input type="time" class="time-input" name="dates[${idx}][schedules][${scheduleCount}][end_time]">
                <input class="input-title" type="text" name="dates[${idx}][schedules][${scheduleCount}][title]">
                <textarea class="input-description" name="dates[${idx}][schedules][${scheduleCount}][description]"></textarea>
                <input class="location-input" type="text" name="dates[${idx}][schedules][${scheduleCount}][location]">
                <input class="location-input" type="url" name="dates[${idx}][schedules][${scheduleCount}][location_url]">
                <button type="button" class="delete-btn delete-btn-under"><i class="fa-solid fa-trash-can"></i> この予定を削除</button>
            </div>`;
            wrapper.insertAdjacentHTML("beforeend", html);
        } else if (e.target.closest(".delete-btn")) {
            const block = e.target.closest(".schedule-block") || e.target.closest(".date-block");
            if (block) block.remove();
        }
    });

    document.getElementById("add-memo-btn").addEventListener("click", function () {
        const html = `
        <div class="memo-block">
            <input class="input-title" type="text" name="memos[${memoIndex}][title]">
            <textarea class="input-description" name="memos[${memoIndex}][content]"></textarea>
            <button type="button" class="delete-btn delete-btn-under"><i class="fa-solid fa-trash-can"></i> このメモを削除</button>
        </div>
        `;
        memosContainer.insertAdjacentHTML("beforeend", html);
        memoIndex++;
    });

    document.getElementById("add-item-btn").addEventListener("click", function () {
        const html = `
        <div class="item-block">
            <input class="input-title" type="text" name="items[${itemIndex}][title]">
            <textarea class="input-description" name="items[${itemIndex}][detail]"></textarea>
            <button type="button" class="delete-btn delete-btn-under"><i class="fa-solid fa-trash-can"></i> このリストを削除</button>
        </div>
        `;
        itemsContainer.insertAdjacentHTML("beforeend", html);
        itemIndex++;
    });

    [memosContainer, itemsContainer].forEach(container => {
        container.addEventListener("click", function (e) {
            if (e.target.closest(".delete-btn")) {
                const block = e.target.closest(".memo-block, .item-block");
                if (block) block.remove();
            }
        });
    });
});
