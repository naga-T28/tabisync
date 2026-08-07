---
id: get_schedules
version: 1
handler: concierge_tools.read_tools.get_schedules
side_effect: none
requires_access: view
timeout_seconds: 2
---

## Description

指定した旅行日の予定一覧を取得する。`days`に`null`を指定するか省略すると全日程を返す。

## Input schema

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "days": {
      "type": ["array", "null"],
      "items": {"type": "integer", "minimum": 1},
      "maxItems": 14
    }
  },
  "required": ["days"]
}
```

## Output schema

`schedules[]`: `id`, `day_index`, `date`, `title`, `start_time`, `end_time`, `description`, `place_name`

## Errors

- `invalid_day`: 旅行期間外の日が指定された。
