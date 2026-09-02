document.addEventListener("DOMContentLoaded", function () {
  const widget = document.getElementById("conciergeFabWidget");
  const button = document.getElementById("conciergeFabButton");
  const bubble = document.getElementById("conciergeFabBubble");
  const bubbleText = document.getElementById("conciergeFabBubbleText");
  const bubbleClose = document.getElementById("conciergeFabBubbleClose");
  const panel = document.getElementById("conciergeFabPanel");
  const panelHeader = document.getElementById("conciergeFabPanelHeader");
  const panelClose = document.getElementById("conciergeFabPanelClose");
  const iframe = document.getElementById("conciergeFabIframe");

  if (!widget || !button || !bubble || !panel || !iframe) return;

  const conciergeUrl = widget.dataset.conciergeUrl || "";
  const pageName = widget.dataset.pageName || "";

  const PAGE_SUGGESTIONS = {
    content_v2: [
      "旅程表の相談、お手伝いしましょうか？",
      "移動時間が心配な区間、チェックしてみませんか？",
      "空き時間にぴったりのスポット、探しましょうか？",
      "この旅程、もっと楽しくできるかも？聞いてみて！",
    ],
    V2_memo: [
      "メモの整理をお手伝いしましょうか？",
      "書き忘れてること、一緒に確認しませんか？",
      "メモ、AIがきれいにまとめますよ！",
    ],
    V2_memo_edit: [
      "メモの整理をお手伝いしましょうか？",
      "書き忘れてること、一緒に確認しませんか？",
      "メモ、AIがきれいにまとめますよ！",
    ],
    V2_list: [
      "持ち物リストの相談に乗りますよ。",
      "忘れ物ないか一緒にチェックしませんか？",
      "行き先や季節に合わせた持ち物、提案できます！",
    ],
    V2_list_edit: [
      "持ち物リストの相談に乗りますよ。",
      "忘れ物ないか一緒にチェックしませんか？",
      "行き先や季節に合わせた持ち物、提案できます！",
    ],
    Wantto: [
      "行きたい場所について相談してみませんか？",
      "気になるスポットの近くのおすすめも教えられますよ！",
      "行きたいリスト、日程に組み込むお手伝いします！",
    ],
    content_edit_v2: [
      "編集で気になることはありませんか？",
      "もっと良い旅程にできるか、一緒に考えましょう！",
      "ここどうしたらいい？と思ったら聞いてください！",
    ],
  };

  const DEFAULT_SUGGESTIONS = [
    "旅の相談、なんでも聞いてください！",
    "気になることがあれば、いつでも聞いてくださいね！",
    "AIコンシェルジュがあなたの旅をサポートします！",
  ];

  function getTimeGreeting() {
    const hour = new Date().getHours();
    if (hour >= 5 && hour < 11) return "おはようございます！";
    if (hour >= 11 && hour < 17) return "こんにちは！";
    if (hour >= 17 && hour < 22) return "こんばんは！";
    return "夜遅くまでお疲れ様です。";
  }

  function pickRandom(list) {
    return list[Math.floor(Math.random() * list.length)];
  }

  function buildBubbleMessage() {
    const suggestions = PAGE_SUGGESTIONS[pageName] || DEFAULT_SUGGESTIONS;
    return `${getTimeGreeting()}${pickRandom(suggestions)}`;
  }

  function dismissBubble() {
    bubble.classList.add("is-hidden");
  }

  function openPanel() {
    if (!iframe.src && conciergeUrl) {
      iframe.src = conciergeUrl;
    }
    panel.classList.add("is-open");
    panel.setAttribute("aria-hidden", "false");
    button.setAttribute("aria-expanded", "true");
    dismissBubble();
  }

  function closePanel() {
    panel.classList.remove("is-open");
    panel.setAttribute("aria-hidden", "true");
    button.setAttribute("aria-expanded", "false");
  }

  function togglePanel() {
    if (panel.classList.contains("is-open")) {
      closePanel();
    } else {
      openPanel();
    }
  }

  if (bubbleText) bubbleText.textContent = buildBubbleMessage();

  button.addEventListener("click", togglePanel);
  if (bubbleClose) bubbleClose.addEventListener("click", dismissBubble);
  if (panelClose) panelClose.addEventListener("click", closePanel);

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && panel.classList.contains("is-open")) {
      closePanel();
    }
  });

  // パネルヘッダーをドラッグしてポップアップの表示位置を移動できるようにする。
  (function enableDrag() {
    if (!panelHeader) return;
    let dragging = false;
    let startX = 0;
    let startY = 0;
    let startLeft = 0;
    let startTop = 0;

    function onPointerDown(event) {
      if (event.target.closest(".concierge-fab-panel-actions")) return;
      const rect = panel.getBoundingClientRect();
      dragging = true;
      startX = event.clientX;
      startY = event.clientY;
      startLeft = rect.left;
      startTop = rect.top;
      panel.style.left = `${startLeft}px`;
      panel.style.top = `${startTop}px`;
      panel.style.right = "auto";
      panel.style.bottom = "auto";
      panel.classList.add("is-dragging");
      event.preventDefault();
    }

    function onPointerMove(event) {
      if (!dragging) return;
      const rect = panel.getBoundingClientRect();
      const maxLeft = Math.max(window.innerWidth - rect.width - 8, 8);
      const maxTop = Math.max(window.innerHeight - rect.height - 8, 8);
      const nextLeft = Math.min(Math.max(startLeft + (event.clientX - startX), 8), maxLeft);
      const nextTop = Math.min(Math.max(startTop + (event.clientY - startY), 8), maxTop);
      panel.style.left = `${nextLeft}px`;
      panel.style.top = `${nextTop}px`;
    }

    function onPointerUp() {
      if (!dragging) return;
      dragging = false;
      panel.classList.remove("is-dragging");
    }

    panelHeader.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
  })();
});
