# Task 010: Font Awesome全量CSSの読み込み方法を見直す

- 観点: SEO / Core Web Vitals
- 優先度: High

## 問題

`base.html`、`base_home.html`、`base-noindex.html`、`demo/v2_base.html`、`tabisync/content/base.html`など、ほぼ全テンプレートが`cdnjs.cloudflare.com`の`font-awesome/6.5.2/css/all.min.css`（全アイコン収録）を最適化なしに同期`<link rel="stylesheet">`で読み込んでいる。各ページで実際に使用しているアイコンは数個〜十数個程度に対し、レンダリングブロッキングCSSとして毎ページFCP/LCPを悪化させている。

`style.css`は`base.html`内で`preload` + `onload`で`rel='stylesheet'`に切り替える非同期読み込みパターンを既に採用しており（`templates/base.html`）、Font Awesomeだけが最適化から取り残されている。

## 実装指示

1. 各テンプレートで実際に使用している`fa-*`クラスを`grep -oE 'fa-[a-z0-9-]+' project_tabisync/templates -r`等で洗い出す。
2. 全量CDN読み込みを、`style.css`と同じ非同期読み込みパターンへ統一するか、使用アイコンのみのサブセットを自己ホストする方式を検討し、方針を決定する。
3. 決定した方式を対象テンプレート全体へ横展開する。
4. 変更後、全公開ページおよびしおり表示・編集画面でアイコンが欠落なく表示されるか目視確認する。

## テスト

- 対象ページでアイコンが欠落・文字化けなく表示される。
- Lighthouse等で、変更前後にレンダリングブロッキングリソースに関する指摘が減っていることを確認する。
- `pipenv run python manage.py test tabisync`が成功する。
