document.addEventListener("DOMContentLoaded", function () {
    var STORAGE_KEY = "tabisync_announcement_dismissed_id";
    var banner = document.querySelector(".announcement-banner");
    if (!banner) return;

    var closeButton = banner.querySelector(".announcement-banner-close");
    if (!closeButton) return;

    var announcementId = banner.getAttribute("data-announcement-id");
    var dismissedId = null;
    try {
        dismissedId = window.localStorage.getItem(STORAGE_KEY);
    } catch (error) {
        dismissedId = null;
    }

    if (dismissedId && dismissedId === announcementId) {
        banner.style.display = "none";
        return;
    }

    closeButton.addEventListener("click", function () {
        banner.style.display = "none";
        try {
            window.localStorage.setItem(STORAGE_KEY, announcementId);
        } catch (error) {
            // localStorageが使えない環境では、次回表示時に再度バナーが表示されます。
        }
    });
});
