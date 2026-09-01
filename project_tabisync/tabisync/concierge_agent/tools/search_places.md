---
id: search_places
version: 1
handler: concierge_tools.place_search_tools.search_places
side_effect: none
requires_access: view
timeout_seconds: 8
---

## Description

Google Maps(Places API)でキーワードから新しい場所を検索する。しおりに未保存の
地点を探すときに使うTool。1回の呼び出しで最大7件まで返す。ここで得られる候補は
まだ「行きたい場所」に保存されていないため、追加する場合は`propose_changes`の
`want_create`(place_idとlat/lngを含める)を経由すること。座標や住所を自分で作文しない。

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

`places[]`(最大7件): `place_id`, `name`, `address`, `lat`, `lng`, `rating`, `user_rating_count`

## Errors

- `not_configured`: Google Maps APIキーが設定されていない。
- `invalid_query`: 検索キーワードが空。
- `api_error`: Google Places APIがエラーを返した。
- `timeout`: Google Places APIへの接続がタイムアウトした。
- `invalid_response`: レスポンスを解釈できなかった。
