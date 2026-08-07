---
id: get_itinerary
version: 1
handler: concierge_tools.read_tools.get_itinerary
side_effect: none
requires_access: view
timeout_seconds: 2
---

## Description

現在のしおりの基本情報(タイトル、説明、旅行期間、総日数)を取得する。まず最初に呼ぶことが多い。

## Input schema

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {}
}
```

## Output schema

- `title`: string
- `subtitle`: string
- `description`: string
- `start_date` / `end_date`: string (`YYYY-MM-DD`。未設定なら空文字)
- `total_days`: integer

## Errors

なし。
