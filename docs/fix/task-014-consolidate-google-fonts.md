# Task 014: Google Fontsのリクエストを統合し使用ウェイトへ絞る

- 観点: SEO / Core Web Vitals
- 優先度: Medium

## 問題

`base.html`、`base_home.html`、`base-noindex.html`、`demo/v2_base.html`、`tabisync/content/base.html`が、`Source Sans Pro`と`Noto Sans JP`を別々の`<link>`（別々の`fonts.googleapis.com`リクエスト）で読み込んでいる。また`Noto+Sans+JP:wght@100..900`は可変フォントの全ウェイト範囲を指定しており、実際にCSSで使用しているウェイトより広い可能性が高い。

## 実装指示

1. `static/scss/`配下で実際に使用している`font-weight`の値を洗い出す。
2. 1つの`<link href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@...&family=Noto+Sans+JP:wght@...&display=swap">`へ統合し、リクエスト数を減らす。
3. 洗い出したウェイトのみを指定し、不要な範囲を削る。
4. 対象の全テンプレートへ同じ統合後のリンクを反映する。
5. 変更後、太字・通常表示箇所を含め主要ページの文字表示が崩れていないか目視確認する。

## テスト

- 対象ページで日本語・英数字の表示ウェイトが変更前と同じに見える（意図せず細字・極太字にならない）。
- ブラウザのNetworkパネルでGoogle Fontsへのリクエスト数が減っていることを確認する。
- `pipenv run python manage.py test tabisync`が成功する。
