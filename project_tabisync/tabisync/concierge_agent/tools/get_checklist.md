---
id: get_checklist
version: 1
handler: concierge_tools.read_tools.get_checklist
side_effect: none
requires_access: view
timeout_seconds: 2
---

## Description

持ち物チェックリストを取得する。

## Input schema

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {}
}
```

## Output schema

`lists[]`: `id`, `title`, `items[]`(`id`, `text`, `checked`)

## Errors

なし。
