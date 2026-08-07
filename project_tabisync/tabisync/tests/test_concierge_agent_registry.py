import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from ..concierge_agent import registry
from ..concierge_agent.checks import check_concierge_agent_definitions
from ..concierge_agent.errors import ConciergeDefinitionError

VALID_TOOL_MD = """---
id: sample_tool
version: 1
handler: concierge_tools.read_tools.get_itinerary
side_effect: none
requires_access: view
timeout_seconds: 2
---

## Description

test tool

## Input schema

```json
{"type": "object", "additionalProperties": false, "properties": {}}
```
"""


class ConciergeRegistryRealDefinitionsTests(SimpleTestCase):
    """実際にリポジトリに存在する5Skill/7Tool Markdownがparse・検証できることを確認する。"""

    def test_real_definitions_build_successfully(self):
        reg = registry.build_registry()
        self.assertEqual(len(reg.all_skill_ids()), 5)

    def test_every_skill_resolves_at_least_one_tool(self):
        reg = registry.build_registry()
        for skill_id in reg.all_skill_ids():
            skill = reg.get_skill(skill_id)
            tool_defs, max_calls = reg.resolve_tools_for_skills([skill])
            self.assertTrue(tool_defs, f"{skill_id} resolved no tools")
            self.assertGreater(max_calls, 0)

    def test_system_check_reports_no_errors(self):
        errors = check_concierge_agent_definitions(None)
        self.assertEqual(errors, [])

    def test_tool_params_are_strict_function_schemas(self):
        reg = registry.build_registry()
        tool_defs, _ = reg.resolve_tools_for_skills([reg.get_skill("trip_planner")])
        params = reg.build_tool_params(tool_defs)
        for tool_param in params:
            self.assertEqual(tool_param["type"], "function")
            self.assertTrue(tool_param["strict"])
            self.assertIs(tool_param["parameters"].get("additionalProperties"), False)


class ConciergeRegistryInvalidDefinitionTests(SimpleTestCase):
    """不正な定義がregistry構築時に検出されることを確認する(system checkでの検出を想定)。"""

    def _build_with_fixture(self, skills=None, tools=None):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            skills_dir = tmp_path / "skills"
            tools_dir = tmp_path / "tools"
            skills_dir.mkdir()
            tools_dir.mkdir()
            for name, content in (tools or {}).items():
                (tools_dir / name).write_text(content, encoding="utf-8")
            for name, content in (skills or {}).items():
                (skills_dir / name).write_text(content, encoding="utf-8")
            with patch.object(registry, "SKILLS_DIR", skills_dir), \
                    patch.object(registry, "TOOLS_DIR", tools_dir):
                return registry.build_registry()

    def test_duplicate_tool_id_raises(self):
        with self.assertRaises(ConciergeDefinitionError):
            self._build_with_fixture(tools={"a.md": VALID_TOOL_MD, "b.md": VALID_TOOL_MD})

    def test_unknown_tool_reference_in_skill_raises(self):
        skill_md = """---
id: sample_skill
version: 1
description: test skill
allowed_tools:
  - unknown_tool
max_tool_calls: 2
---

body
"""
        with self.assertRaises(ConciergeDefinitionError):
            self._build_with_fixture(tools={"a.md": VALID_TOOL_MD}, skills={"s.md": skill_md})

    def test_missing_required_tool_field_raises(self):
        tool_md_missing_timeout = """---
id: broken_tool
version: 1
handler: concierge_tools.read_tools.get_itinerary
side_effect: none
requires_access: view
---

## Description
test

## Input schema
```json
{"type": "object", "additionalProperties": false, "properties": {}}
```
"""
        with self.assertRaises(ConciergeDefinitionError):
            self._build_with_fixture(tools={"a.md": tool_md_missing_timeout})

    def test_missing_required_skill_field_raises(self):
        skill_md_missing_max_calls = """---
id: sample_skill
version: 1
description: test skill
allowed_tools:
  - sample_tool
---

body
"""
        with self.assertRaises(ConciergeDefinitionError):
            self._build_with_fixture(
                tools={"a.md": VALID_TOOL_MD},
                skills={"s.md": skill_md_missing_max_calls},
            )

    def test_excessive_max_tool_calls_raises(self):
        skill_md = """---
id: greedy_skill
version: 1
description: test skill
allowed_tools:
  - sample_tool
max_tool_calls: 999
---

body
"""
        with self.assertRaises(ConciergeDefinitionError):
            self._build_with_fixture(tools={"a.md": VALID_TOOL_MD}, skills={"s.md": skill_md})

    def test_unknown_handler_raises(self):
        tool_md = """---
id: bad_handler_tool
version: 1
handler: concierge_tools.read_tools.not_a_real_function
side_effect: none
requires_access: view
timeout_seconds: 2
---

## Description
test

## Input schema
```json
{"type": "object", "additionalProperties": false, "properties": {}}
```
"""
        with self.assertRaises(ConciergeDefinitionError):
            self._build_with_fixture(tools={"a.md": tool_md})

    def test_missing_additional_properties_false_raises(self):
        tool_md = """---
id: loose_tool
version: 1
handler: concierge_tools.read_tools.get_itinerary
side_effect: none
requires_access: view
timeout_seconds: 2
---

## Description
test

## Input schema
```json
{"type": "object", "properties": {}}
```
"""
        with self.assertRaises(ConciergeDefinitionError):
            self._build_with_fixture(tools={"a.md": tool_md})

    def test_invalid_side_effect_raises(self):
        tool_md = """---
id: bad_side_effect_tool
version: 1
handler: concierge_tools.read_tools.get_itinerary
side_effect: destructive
requires_access: view
timeout_seconds: 2
---

## Description
test

## Input schema
```json
{"type": "object", "additionalProperties": false, "properties": {}}
```
"""
        with self.assertRaises(ConciergeDefinitionError):
            self._build_with_fixture(tools={"a.md": tool_md})

    def test_empty_definitions_directory_raises(self):
        with self.assertRaises(ConciergeDefinitionError):
            self._build_with_fixture(tools={})
