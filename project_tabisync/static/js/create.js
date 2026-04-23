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
    
    endDate.addEventListener("change", function () {
        if (startDate.value && this.value && this.value < startDate.value) {
            alert("終了日は開始日以降を選択してください。");
            this.value = "";
        }
    });
});

