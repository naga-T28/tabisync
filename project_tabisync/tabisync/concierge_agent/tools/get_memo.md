---
id: get_memo
version: 1
handler: concierge_tools.read_tools.get_memo
side_effect: none
requires_access: view
timeout_seconds: 2
---

## Description

しおりのメモを、タグを除去したプレーンテキストとして取得する。

## Input schema

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {}
}
```

## Output schema

`notes[]`: `content`(タグ除去済みの本文)

## Errors

なし。
