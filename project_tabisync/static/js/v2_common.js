(function (global) {
    "use strict";

    const STATUS_ICON_CLASS_MAP = {
        idle: "fa-circle-info",
        saving: "fa-rotate fa-spin",
        saved: "fa-circle-check",
        error: "fa-circle-exclamation",
        dirty: "fa-pen",
    };

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(";").shift();
        return "";
    }

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function createId(prefix) {
        return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
    }

    function statusIconClass(status) {
        return `fa-solid ${STATUS_ICON_CLASS_MAP[status] || STATUS_ICON_CLASS_MAP.idle}`;
    }

    function runOnboardingTour(storageKey, steps, forceStart) {
        if (!window.driver || !window.driver.js || !window.driver.js.driver) return;
        if (!forceStart && window.localStorage.getItem(storageKey)) return;

        const driverObj = window.driver.js.driver({
            animate: true,
            overlayOpacity: 0.75,
            showProgress: true,
            nextBtnText: "次へ",
            prevBtnText: "戻る",
            doneBtnText: "完了",
            onDestroyed: function () {
                window.localStorage.setItem(storageKey, "true");
            },
            steps: steps,
        });

        driverObj.drive();
    }

    // storageKey: localStorageに既読フラグを保存するキー
    // buildSteps: driver.js のstep配列を返す関数（呼び出すたびに再評価される）
    function initOnboardingTour(storageKey, buildSteps) {
        function start(forceStart) {
            runOnboardingTour(storageKey, buildSteps(), forceStart);
        }

        window.startContentTour = function () {
            start(true);
        };

        start(false);

        const tourButton = document.getElementById("content-tour-button");
        if (tourButton) {
            tourButton.addEventListener("click", function () {
                start(true);
            });
        }
    }

    global.TabiSyncCommon = {
        getCookie: getCookie,
        escapeHtml: escapeHtml,
        createId: createId,
        statusIconClass: statusIconClass,
        initOnboardingTour: initOnboardingTour,
    };
})(window);
