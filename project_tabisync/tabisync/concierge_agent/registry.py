from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Tuple

from .errors import ConciergeDefinitionError
from .markdown_defs import (
    extract_json_fences,
    parse_float_field,
    parse_front_matter,
    parse_int_field,
    parse_list_field,
    require_keys,
)

SKILLS_DIR = Path(__file__).resolve().parent / "skills"
TOOLS_DIR = Path(__file__).resolve().parent / "tools"

_TOOL_HANDLER_ALLOWLIST_CACHE = None


def _build_tool_handler_allowlist():
    # concierge_tools はTool実装から共通view helper(views.itinerary_helpers等)へ依存しており、
    # モジュールトップレベルでimportすると tabisync.views パッケージのロードを巻き込み、
    # views.concierge -> concierge_agent.registry との循環importになる。
    # そのためこの構築自体を初回呼び出し時まで遅延させる。
    from ..concierge_tools import place_search_tools, proposal_tools, read_tools, ui_tools

    return {
        "concierge_tools.read_tools.get_itinerary": read_tools.get_itinerary,
        "concierge_tools.read_tools.get_schedules": read_tools.get_schedules,
        "concierge_tools.read_tools.get_want_to_go": read_tools.get_want_to_go,
        "concierge_tools.read_tools.get_memo": read_tools.get_memo,
        "concierge_tools.read_tools.get_checklist": read_tools.get_checklist,
        "concierge_tools.proposal_tools.propose_changes": proposal_tools.propose_changes,
        "concierge_tools.ui_tools.show_map": ui_tools.show_map,
        "concierge_tools.place_search_tools.search_places": place_search_tools.search_places,
    }


def get_tool_handler_allowlist():
    """Markdown側の自由記述に実行権限を渡さないための唯一の実行可能経路。
    ここに無いhandler文字列はimportlib等で動的解決せず、起動時エラーにする。"""
    global _TOOL_HANDLER_ALLOWLIST_CACHE
    if _TOOL_HANDLER_ALLOWLIST_CACHE is None:
        _TOOL_HANDLER_ALLOWLIST_CACHE = _build_tool_handler_allowlist()
    return _TOOL_HANDLER_ALLOWLIST_CACHE

REQUIRED_SKILL_KEYS = ("id", "version", "description", "allowed_tools", "max_tool_calls")
REQUIRED_TOOL_KEYS = ("id", "version", "handler", "side_effect", "requires_access", "timeout_seconds")
VALID_SIDE_EFFECTS = {"none", "proposal_only"}
VALID_REQUIRES_ACCESS = {"view", "edit"}

# Skill Markdown定義そのものが持てる理想上限(明らかに異常な値をはじくための緩い安全網)。
# 実行時に実際へ適用される上限は、usage.CONCIERGE_AGENT_MAX_TOOL_CALLS_PER_RUNとの
# min()で別途決まる(registryはSkill定義の妥当性のみを検証する)。
ABSOLUTE_MAX_TOOL_CALLS_PER_SKILL = 20


@dataclass(frozen=True)
class ToolDef:
    id: str
    version: int
    handler: Callable
    side_effect: str
    requires_access: str
    timeout_seconds: float
    description: str
    input_schema: dict


@dataclass(frozen=True)
class SkillDef:
    id: str
    version: int
    title: str
    description: str
    allowed_tools: Tuple[str, ...]
    max_tool_calls: int
    instructions_text: str


def resolve_handler(handler_path, def_id_for_error):
    allowlist = get_tool_handler_allowlist()
    if handler_path not in allowlist:
        raise ConciergeDefinitionError(f"{def_id_for_error}: 未許可のhandlerです: {handler_path}")
    return allowlist[handler_path]


def _load_markdown_files(directory):
    files = sorted(directory.glob("*.md"))
    if not files:
        raise ConciergeDefinitionError(f"定義ファイルが見つかりません: {directory}")
    loaded = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        front_matter, body = parse_front_matter(text)
        loaded.append((path, front_matter, body))
    return loaded


def _extract_section(body, heading):
    lines = body.splitlines()
    collecting = False
    collected = []
    for line in lines:
        if line.strip().startswith("## "):
            if collecting:
                break
            collecting = line.strip()[3:].strip().lower() == heading.lower()
            continue
        if collecting:
            collected.append(line)
    return "\n".join(collected).strip()


def _build_tool_def(path, front_matter, body):
    require_keys(front_matter, REQUIRED_TOOL_KEYS, path.name)
    tool_id = str(front_matter["id"]).strip()
    if not tool_id:
        raise ConciergeDefinitionError(f"{path.name}: idが空です。")

    version = parse_int_field(front_matter, "version", tool_id)
    handler_path = str(front_matter["handler"]).strip()
    handler = resolve_handler(handler_path, tool_id)

    side_effect = str(front_matter["side_effect"]).strip()
    if side_effect not in VALID_SIDE_EFFECTS:
        raise ConciergeDefinitionError(f"{tool_id}: side_effectが不正です: {side_effect!r}")

    requires_access = str(front_matter["requires_access"]).strip()
    if requires_access not in VALID_REQUIRES_ACCESS:
        raise ConciergeDefinitionError(f"{tool_id}: requires_accessが不正です: {requires_access!r}")

    timeout_seconds = parse_float_field(front_matter, "timeout_seconds", tool_id)
    if timeout_seconds <= 0:
        raise ConciergeDefinitionError(f"{tool_id}: timeout_secondsは正の数である必要があります。")

    fences = extract_json_fences(body)
    if not fences:
        raise ConciergeDefinitionError(f"{tool_id}: Input schemaのJSONブロックが見つかりません。")
    input_schema = fences[0]
    if not isinstance(input_schema, dict) or input_schema.get("additionalProperties") is not False:
        raise ConciergeDefinitionError(f"{tool_id}: Input schemaにadditionalProperties: falseが必要です。")

    description = _extract_section(body, "Description")

    return ToolDef(
        id=tool_id,
        version=version,
        handler=handler,
        side_effect=side_effect,
        requires_access=requires_access,
        timeout_seconds=timeout_seconds,
        description=description,
        input_schema=input_schema,
    )


def _build_skill_def(path, front_matter, body, known_tool_ids):
    require_keys(front_matter, REQUIRED_SKILL_KEYS, path.name)
    skill_id = str(front_matter["id"]).strip()
    if not skill_id:
        raise ConciergeDefinitionError(f"{path.name}: idが空です。")

    version = parse_int_field(front_matter, "version", skill_id)
    description = str(front_matter["description"]).strip()
    if not description:
        raise ConciergeDefinitionError(f"{skill_id}: descriptionが空です。")

    allowed_tools = tuple(str(t).strip() for t in parse_list_field(front_matter, "allowed_tools", skill_id))
    if not allowed_tools:
        raise ConciergeDefinitionError(f"{skill_id}: allowed_toolsが空です。")

    unknown_tools = [tool_id for tool_id in allowed_tools if tool_id not in known_tool_ids]
    if unknown_tools:
        raise ConciergeDefinitionError(f"{skill_id}: 未知のToolを参照しています: {unknown_tools}")

    max_tool_calls = parse_int_field(front_matter, "max_tool_calls", skill_id)
    if max_tool_calls < 0 or max_tool_calls > ABSOLUTE_MAX_TOOL_CALLS_PER_SKILL:
        raise ConciergeDefinitionError(
            f"{skill_id}: max_tool_calls={max_tool_calls} は許容上限"
            f"{ABSOLUTE_MAX_TOOL_CALLS_PER_SKILL}を超えています。"
        )

    title = str(front_matter.get("title") or skill_id).strip()

    return SkillDef(
        id=skill_id,
        version=version,
        title=title,
        description=description,
        allowed_tools=allowed_tools,
        max_tool_calls=max_tool_calls,
        instructions_text=body.strip(),
    )


class ConciergeRegistry:
    def __init__(self, skills, tools):
        self._skills = {skill.id: skill for skill in skills}
        self._tools = {tool.id: tool for tool in tools}

    def get_skill(self, skill_id):
        return self._skills.get(skill_id)

    def get_tool(self, tool_id):
        return self._tools.get(tool_id)

    def all_skill_ids(self):
        return list(self._skills.keys())

    def resolve_skills(self, skill_ids):
        resolved = []
        for skill_id in skill_ids or []:
            skill = self._skills.get(skill_id)
            if skill is not None and skill not in resolved:
                resolved.append(skill)
        return resolved

    def resolve_tools_for_skills(self, skills):
        """選択されたSkillのallowed_toolsの和集合を返す。max_tool_callsは各Skillの中の
        最大値を採る(複数の目的を同時に達成する場合、より緩やかな側に合わせる)。
        最終的な実行時上限はusage.RunUsageCountersがグローバル上限とのmin()で決める。
        """
        if not skills:
            return [], 0

        tool_ids = []
        for skill in skills:
            for tool_id in skill.allowed_tools:
                if tool_id not in tool_ids:
                    tool_ids.append(tool_id)

        tool_defs = [self._tools[tool_id] for tool_id in tool_ids if tool_id in self._tools]
        max_tool_calls = max(skill.max_tool_calls for skill in skills)
        return tool_defs, max_tool_calls

    @staticmethod
    def build_tool_params(tool_defs):
        return [
            {
                "type": "function",
                "name": tool.id,
                "description": tool.description or tool.id,
                "parameters": tool.input_schema,
                "strict": True,
            }
            for tool in tool_defs
        ]


def build_registry():
    tool_files = _load_markdown_files(TOOLS_DIR)
    tool_defs = []
    seen_tool_ids = set()
    for path, front_matter, body in tool_files:
        tool_def = _build_tool_def(path, front_matter, body)
        if tool_def.id in seen_tool_ids:
            raise ConciergeDefinitionError(f"Tool idが重複しています: {tool_def.id}")
        seen_tool_ids.add(tool_def.id)
        tool_defs.append(tool_def)

    skill_files = _load_markdown_files(SKILLS_DIR)
    skill_defs = []
    seen_skill_ids = set()
    for path, front_matter, body in skill_files:
        skill_def = _build_skill_def(path, front_matter, body, seen_tool_ids)
        if skill_def.id in seen_skill_ids:
            raise ConciergeDefinitionError(f"Skill idが重複しています: {skill_def.id}")
        seen_skill_ids.add(skill_def.id)
        skill_defs.append(skill_def)

    return ConciergeRegistry(skill_defs, tool_defs)


_REGISTRY_CACHE = None


def get_registry():
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is None:
        _REGISTRY_CACHE = build_registry()
    return _REGISTRY_CACHE


def reset_registry_cache():
    """テスト用。不正なfixtureディレクトリを差し替えて検証する際にキャッシュをクリアする。"""
    global _REGISTRY_CACHE
    _REGISTRY_CACHE = None
