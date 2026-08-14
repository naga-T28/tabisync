# Task 009: 未使用のFlatpickr読み込みを削除する

- 観点: SEO / Core Web Vitals
- 優先度: High

## 問題

`base.html`（FAQ・プロフィール・お問い合わせ・作成・ガイド5ページ・更新情報・404が継承）、`base-noindex.html`、`tabisync/list.html`、`tabisync/memo.html`、`tabisync/edit.html`、`tabisync/content.html`、`tabisync/content/base.html`、`tabisync/content/concierge_v2.html`が、Flatpickrの CSS（`flatpickr.min.css`）とJS本体を`async`/`defer`なしの同期`<script>`で読み込んでいる。

リポジトリ全体を`flatpickr(`で検索しても呼び出し箇所が1件も見つからず、日付入力（`create.html`含む）はすべてネイティブの`<input type="date">`を使用している。レンダリングブロッキングリソースとして、ホーム以外のほぼ全公開ページとしおり表示・編集画面のLCP/FCPを不必要に悪化させている疑いが強い。`docs/task/task-006-core-web-vitals-performance.md`の「1. Flatpickrが全ページで読み込まれているが、どこにも実装がない」と同一課題。

## 実装指示

1. `static/js/`および全テンプレートで`flatpickr(`・`Flatpickr(`・`data-flatpickr`等の呼び出しが本当に存在しないことを最終確認する。
2. 未使用と確認できたら、上記全テンプレートからFlatpickrのCSS/JSタグを削除する。
3. 日付入力を含む画面（`create.html`、しおり編集画面）をローカルで実際に開き、日付選択が引き続き問題なく動作することを確認する。
4. 削除後、対象ページをブラウザのDevToolsで開き、コンソールエラーが出ていないことを確認する。

## テスト

- しおり作成フォーム・編集画面の日付入力欄が変更前と同じ挙動で動作する（回帰なし）。
- 削除対象テンプレートのレンダリング結果に`flatpickr`という文字列が含まれない。
- `pipenv run python manage.py test tabisync`が成功する。
