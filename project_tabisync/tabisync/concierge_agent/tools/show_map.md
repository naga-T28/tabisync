---
id: show_map
version: 1
handler: concierge_tools.ui_tools.show_map
side_effect: none
requires_access: view
timeout_seconds: 2
---

## Description

「行きたい場所」リストに保存済みの場所を地図表示するための構造化データを返す。
HTML・URL・座標は本Toolがサーバー側で組み立てるため、モデル自身がURLや座標を生成する必要はない。
新規の地点検索や外部の最新情報取得は行わない(未保存の場所は指定できない)。

## Input schema

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "want_to_go_ids": {
      "type": "array",
      "items": {"type": "integer", "minimum": 1},
      "minItems": 1,
      "maxItems": 8
    },
    "title": {"type": "string", "maxLength": 60}
  },
  "required": ["want_to_go_ids", "title"]
}
```

## Output schema

`places[]`: `id`, `name`, `address`, `lat`, `lng`, `place_id`, `maps_url`(サーバー側で組み立て済みのGoogle Maps検索URL)

## Errors

- `no_places_found`: 指定されたidが現在のしおりに存在しない。
