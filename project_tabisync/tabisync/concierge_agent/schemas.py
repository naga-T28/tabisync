MAX_REPLY_MARKDOWN_LENGTH = 4000
MAX_UI_COMPONENTS = 3
MAX_EDIT_ACTIONS = 12


def build_skill_routing_schema(skill_ids):
    """select_skills()で使うstructured outputスキーマ。enumはregistryから動的生成する。"""
    return {
        "name": "concierge_skill_routing",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "skill_ids": {
                    "type": "array",
                    "items": {"type": "string", "enum": list(skill_ids)},
                    "minItems": 1,
                    "maxItems": max(len(skill_ids), 1),
                },
                "reason": {"type": "string"},
            },
            "required": ["skill_ids", "reason"],
        },
    }
