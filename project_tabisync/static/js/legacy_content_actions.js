(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {
        initShareButton();
        initCopyUrlBox();
        initMobileLinkSimplify();
        registerServiceWorker();
    });

    function initShareButton() {
        const shareButton = document.getElementById("share-button");
        if (!shareButton) return;
        const shareText = shareButton.dataset.shareText || "旅のしおりを共有します";

        shareButton.addEventListener("click", function () {
            if (navigator.share) {
                navigator.share({
                    title: document.title,
                    text: shareText,
                    url: window.location.href,
                }).catch(function () {});
            } else if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(window.location.href)
                    .then(function () {
                        alert("URLをクリップボードにコピーしました。共有したい場所に貼り付けてください。");
                    })
                    .catch(function () {
                        alert("クリップボードへのコピーに失敗しました。手動でURLをコピーしてください。\n" + window.location.href);
                    });
            } else {
                prompt("URLをコピーしてください:", window.location.href);
            }
        });
    }

    function initCopyUrlBox() {
        const urlBox = document.getElementById("copy-url-box");
        const urlText = document.getElementById("copy-url-text");
        if (!urlBox || !urlText) return;

        urlBox.addEventListener("click", function () {
            const textToCopy = urlText.textContent;
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(textToCopy)
                    .then(function () { alert("URLをコピーしました！"); })
                    .catch(function () { prompt("コピーできませんでした。手動でコピーしてください：", textToCopy); });
            } else {
                prompt("コピーできませんでした。手動でコピーしてください：", textToCopy);
            }
        });
    }

    function initMobileLinkSimplify() {
        const MOBILE_MAX_WIDTH = 768;
        if (window.innerWidth > MOBILE_MAX_WIDTH) return;

        document.querySelectorAll(".url-content a").forEach(function (link) {
            try {
                const url = new URL(link.href);
                const domain = url.hostname.replace(/^www\./, "");

                const icon = document.createElement("i");
                icon.className = "fa-solid fa-link";
                icon.setAttribute("aria-hidden", "true");

                link.textContent = "";
                link.appendChild(icon);
                link.append(" " + domain);
                link.title = link.href;
            } catch (e) {
                // URLとして解析できない場合は何もしない
            }
        });
    }

    function registerServiceWorker() {
        if (!("serviceWorker" in navigator)) return;
        const swUrl = document.body.dataset.swUrl;
        if (!swUrl) return;

        navigator.serviceWorker.register(swUrl).catch(function (err) {
            console.error("SW 登録失敗:", err);
        });
    }
})();
