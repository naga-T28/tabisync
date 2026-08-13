# Task 011: 主要画像にwidth/height（またはaspect-ratio）を設定してCLSを防ぐ

- 観点: SEO / Core Web Vitals
- 優先度: High

## 問題

ホームのヒーロー画像（`templates/home.html`、デスクトップでのLCP候補）と、全ページ共通のヘッダーロゴ（`templates/base.html`、`base_home.html`、`base-noindex.html`）、404画像（`templates/404.html`）に`width`/`height`属性がない。CSS側も`.logo-image { width: auto; height: 40px; }`（`static/scss/home/_header.scss`）と幅が`auto`のままのため、画像読み込み完了まで実際の幅が確定せずレイアウトシフト（CLS）の要因になる。

`docs/guide_sample.html`や`tabisync/content/content.html`のQRコード画像では既に`width`/`height`が指定されており、社内に対策パターンは存在する。

## 実装指示

1. 対象画像（`home-hero-product.webp`、各ロゴ画像、`404.webp`）の実ファイルの縦横比を確認する。
2. 各`<img>`タグに実寸に応じた`width`/`height`属性を追加する。
3. ロゴ画像はCSS側の`width: auto`を固定値または`aspect-ratio`指定に変更し、`static/scss/home/_header.scss`のPC時`height: 40px`・スマホ時`height: 52px`と矛盾しないようにする。
4. ホームのヒーロー画像は、LCP候補である点を踏まえ`fetchpriority="high"`の付与も合わせて検討する（`docs/task/task-006-core-web-vitals-performance.md`の画像最適化項目と合わせて実施可）。
5. 変更後、デスクトップ・モバイル双方で画像が歪んでいないか、レイアウトがガタつかないか目視確認する。

## テスト

- Chrome DevToolsのPerformanceパネルまたはLighthouseでCLSスコアが悪化していないことを確認する。
- 対象画像が意図した比率で表示され、歪みがないことを目視確認する。
- `pipenv run python manage.py test tabisync`が成功する。
