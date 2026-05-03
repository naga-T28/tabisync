document.addEventListener("DOMContentLoaded", function () {
    const MAX_ITINERARY_DAYS = 30;
    const startDate = document.getElementById("startDate");
    const endDate = document.getElementById("endDate");

    if (!startDate || !endDate) return;

    function parseLocalDate(value) {
        if (!value) return null;
        const parts = value.split("-");
        if (parts.length !== 3) return null;
        return new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    }

    function formatLocalDate(date) {
        const yyyy = date.getFullYear();
        const mm = String(date.getMonth() + 1).padStart(2, "0");
        const dd = String(date.getDate()).padStart(2, "0");
        return `${yyyy}-${mm}-${dd}`;
    }

    function getMaxEndDateValue(startValue) {
        const date = parseLocalDate(startValue);
        if (!date) return "";
        date.setDate(date.getDate() + MAX_ITINERARY_DAYS - 1);
        return formatLocalDate(date);
    }

    function validateDateRange() {
        if (!startDate.value || !endDate.value) return true;

        if (endDate.value < startDate.value) {
            alert("終了日は開始日以降を選択してください。");
            endDate.value = "";
            return false;
        }

        const maxEndDate = getMaxEndDateValue(startDate.value);
        if (maxEndDate && endDate.value > maxEndDate) {
            alert(`日程は最大${MAX_ITINERARY_DAYS}日間まで登録できます。`);
            endDate.value = "";
            return false;
        }

        return true;
    }

    startDate.addEventListener("input", function () {
        if (!this.value) return;

        endDate.min = this.value;
        endDate.max = getMaxEndDateValue(this.value);

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
        validateDateRange();
    });
});
