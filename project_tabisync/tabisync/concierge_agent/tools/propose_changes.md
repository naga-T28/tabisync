---
id: propose_changes
version: 1
handler: concierge_tools.proposal_tools.propose_changes
side_effect: proposal_only
requires_access: view
timeout_seconds: 3
---

## Description

しおりの編集候補を検証だけ行い、DBへは保存せずに返す。実際の適用はユーザーが確認画面で
承認したあとに別経路(`concierge_v2_apply_changes`)で行われるため、このToolの呼び出し自体は
しおりを一切変更しない。呼び出し後は「変更しました」ではなく「変更候補を提案します」と表現する。

## Input schema

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "actions": {
      "type": "array",
      "minItems": 1,
      "maxItems": 12,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "action": {
            "type": "string",
            "enum": [
              "schedule_create",
              "schedule_update",
              "schedule_delete",
              "want_create",
              "want_update",
              "want_delete",
              "memo_append",
              "checklist_add_item"
            ]
          },
          "id": {"type": ["integer", "null"]},
          "day": {"type": ["integer", "null"]},
          "title": {"type": ["string", "null"]},
          "description": {"type": ["string", "null"]},
          "start_time": {"type": ["string", "null"]},
          "end_time": {"type": ["string", "null"]},
          "icon": {"type": ["string", "null"]},
          "place_name": {"type": ["string", "null"]},
          "address": {"type": ["string", "null"]},
          "place_id": {"type": ["string", "null"]},
          "lat": {"type": ["number", "null"]},
          "lng": {"type": ["number", "null"]},
          "rating": {"type": ["number", "null"]},
          "memo": {"type": ["string", "null"]},
          "priority": {"type": ["integer", "null"]},
          "content": {"type": ["string", "null"]},
          "items": {
            "type": "array",
            "items": {"type": "string"}
          }
        },
        "required": [
          "action",
          "id",
          "day",
          "title",
          "description",
          "start_time",
          "end_time",
          "icon",
          "place_name",
          "address",
          "place_id",
          "lat",
          "lng",
          "rating",
          "memo",
          "priority",
          "content",
          "items"
        ]
      }
    }
  },
  "required": ["actions"]
}
```

## Output schema

- `accepted[]`: 検証に通った候補(元のaction項目 + `preview_label`)
- `rejected[]`: `index`(actions内の位置)と`reason`(却下理由)

## Errors

なし(個々のaction検証エラーは`rejected[].reason`へ格納され、例外にはならない)。
