---
id: search_app_help
version: 1
handler: concierge_tools.help_tools.search_app_help
side_effect: none
requires_access: view
timeout_seconds: 2
---

## Description

TabiSync自体の機能・使い方を説明した公式ヘルプページ(使い方ガイド・よくある質問)から、
質問に近い内容を検索する。埋め込みモデルは使わず、キーワードの一致度でスコアリングする
軽量な検索。しおりの中身(旅程・行きたい場所・持ち物・メモ)は検索対象に含まない。

## Input schema

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "query": {"type": "string", "minLength": 1, "maxLength": 200}
  },
  "required": ["query"]
}
```

## Output schema

`results[]`(最大3件、関連度順): `title`, `summary`, `url`(サーバー側で組み立て済みの絶対URL)

## Errors

- `invalid_query`: 検索キーワードが空。
