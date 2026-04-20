// 日程未定チェックボックスの状態に応じて、日付入力欄と日数入力欄の表示・非表示を切り替える
document.addEventListener("DOMContentLoaded", function () {
    const undecidedCheck = document.getElementById("undecidedCheck");
    const dateInputs = document.getElementById("dateInputs");
    const daysInput = document.getElementById("daysInput");
    const startDate = document.getElementById("startDate");
    const endDate = document.getElementById("endDate");

    undecidedCheck.addEventListener("change", function () {

        if (this.checked) {
            // 日程未定モード
            dateInputs.style.opacity = "0.5";
            startDate.disabled = true;
            endDate.disabled = true;

            daysInput.style.display = "block";

        } else {
            // 日付指定モード
            dateInputs.style.opacity = "1";
            startDate.disabled = false;
            endDate.disabled = false;

            daysInput.style.display = "none";
        }
    });
});   

document.addEventListener("DOMContentLoaded", function () {
    const startDate = document.getElementById("startDate");
    const endDate = document.getElementById("endDate");

    if (!startDate || !endDate) return;

    startDate.addEventListener("input", function () {
        if (!this.value) return;

        endDate.min = this.value;

        if (endDate.value && endDate.value < this.value) {
            endDate.value = "";
        }

        if (!endDate.value) {
            const parts = this.value.split("-"); // ["2026","02","11"]
            const year = parseInt(parts[0], 10);
            const month = parseInt(parts[1], 10) - 1; // 月は0始まり
            const day = parseInt(parts[2], 10);

            const date = new Date(year, month, day + 1);

            const yyyy = date.getFullYear();
            const mm = ("0" + (date.getMonth() + 1)).slice(-2);
            const dd = ("0" + date.getDate()).slice(-2);

            endDate.value = `${yyyy}-${mm}-${dd}`;
        }
    });
});



endDate.addEventListener("change", function () {
    if (this.value < startDate.value) {
        alert("終了日は開始日以降を選択してください。");
        this.value = "";
    }
});


