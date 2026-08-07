import json
import re

from .errors import ConciergeDefinitionError

_FRONT_MATTER_DELIM = "---"
_JSON_FENCE_PATTERN = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


def parse_front_matter(text):
    """先頭の`---`区切りブロックを、フラットな`key: value`と1階層の`key:\\n  - item`形式で
    解釈する自前の軽量パーサ。

    このアプリのSkill/Tool定義ファイルだけが対象であり、ネストしたマッピングや複数行文字列など
    フルYAMLの機能は扱わない。新規依存(PyYAML等)を増やさず、対象を絞ることで
    パーサ自体の複雑さと攻撃面を小さく保つための意図的な設計判断。

    戻り値: (front_matter: dict, body: str)
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONT_MATTER_DELIM:
        raise ConciergeDefinitionError("front matterは先頭の`---`で始まる必要があります。")

    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == _FRONT_MATTER_DELIM:
            end_index = index
            break
    if end_index is None:
        raise ConciergeDefinitionError("front matterを閉じる`---`が見つかりません。")

    body = "\n".join(lines[end_index + 1:]).strip("\n")
    front_matter = {}
    current_list_key = None

    for raw_line in lines[1:end_index]:
        if not raw_line.strip():
            continue

        if raw_line[:1] in (" ", "\t"):
            stripped = raw_line.strip()
            if not stripped.startswith("- "):
                raise ConciergeDefinitionError(f"front matterのリスト項目が不正です: {raw_line!r}")
            if current_list_key is None:
                raise ConciergeDefinitionError(f"リスト項目の親keyが不明です: {raw_line!r}")
            front_matter[current_list_key].append(stripped[2:].strip())
            continue

        if ":" not in raw_line:
            raise ConciergeDefinitionError(f"front matterの行が不正です: {raw_line!r}")

        key, _, value = raw_line.partition(":")
        key = key.strip()
        value = value.strip()
        if not key:
            raise ConciergeDefinitionError(f"front matterのkeyが空です: {raw_line!r}")

        if value == "":
            front_matter[key] = []
            current_list_key = key
        else:
            front_matter[key] = value
            current_list_key = None

    return front_matter, body


def extract_json_fences(body):
    """本文中の```json ... ```フェンスをすべて抽出し、パース済みオブジェクトのリストで返す。"""
    results = []
    for match in _JSON_FENCE_PATTERN.finditer(body):
        try:
            results.append(json.loads(match.group(1)))
        except json.JSONDecodeError as exc:
            raise ConciergeDefinitionError(f"本文中のJSONを解釈できません: {exc}") from exc
    return results


def require_keys(front_matter, keys, def_id_for_error):
    missing = [key for key in keys if key not in front_matter]
    if missing:
        raise ConciergeDefinitionError(
            f"{def_id_for_error}: 必須front matterが不足しています: {', '.join(missing)}"
        )


def parse_int_field(front_matter, key, def_id_for_error):
    raw = front_matter.get(key)
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ConciergeDefinitionError(f"{def_id_for_error}: {key}は整数である必要があります: {raw!r}")


def parse_float_field(front_matter, key, def_id_for_error):
    raw = front_matter.get(key)
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise ConciergeDefinitionError(f"{def_id_for_error}: {key}は数値である必要があります: {raw!r}")


def parse_list_field(front_matter, key, def_id_for_error):
    raw = front_matter.get(key, [])
    if not isinstance(raw, list):
        raise ConciergeDefinitionError(f"{def_id_for_error}: {key}はリストである必要があります: {raw!r}")
    return raw
