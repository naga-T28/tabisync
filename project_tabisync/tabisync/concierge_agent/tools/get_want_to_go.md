---
id: get_want_to_go
version: 1
handler: concierge_tools.read_tools.get_want_to_go
side_effect: none
requires_access: view
timeout_seconds: 2
---

## Description

「行きたい場所」リストを取得する。名称・予定日・優先度・メモ・住所のみを含み、緯度経度や
Google Place IDは含まない(座標が必要な場合は`show_map`を使う)。

## Input schema

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {}
}
```

## Output schema

`places[]`: `id`, `name`, `planned_day`, `priority`, `memo`, `address`

## Errors

なし。
