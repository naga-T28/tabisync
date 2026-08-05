# Task 002: チェックリストJSONの安全なHTML埋め込みに変更する

- 観点: セキュリティ
- 優先度: High

## 問題

`templates/tabisync/content/list_v2.html` と `list_edit_v2.html` は、ユーザー入力を含む `checklists_json` を `|safe` で `<script>` 内へ出力しています。項目に `</script>` 等を保存するとscript要素を脱出でき、保存型XSSにつながります。

メモ画面では既にDjangoの `json_script` を使用しており、安全な実装例があります。

## 実装指示

1. `checklists` オブジェクトをテンプレートへ渡し、`json_script` で埋め込む。
2. View側の二重JSON化用 `checklists_json` を削除する。
3. JavaScriptは対象要素の `textContent` を `JSON.parse` する。
4. `|safe` でユーザー入力をscript/HTMLへ渡している箇所を再検索し、同種の箇所も安全なDOM APIまたは適切なエスケープへ置換する。

## テスト

- タイトル・項目に `</script><script>...`、`<img onerror=...>`、引用符、`&` を含めても実行されず、文字列として復元される。
- 閲覧用・編集用の両テンプレートを検証する。
- 正常な日本語、絵文字、改行が壊れない。

