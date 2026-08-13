class ConciergeDefinitionError(Exception):
    """Skill/Tool Markdown定義の不整合。起動時のregistry構築(system check)で検出される。"""


class ConciergeAgentError(Exception):
    """Agent loop実行時の一般エラー。ユーザー向けメッセージは公開エラーへ変換すること。"""


class ToolExecutionError(ConciergeAgentError):
    def __init__(self, tool_id, error_code, message=None):
        self.tool_id = tool_id
        self.error_code = error_code
        super().__init__(message or f"{tool_id}: {error_code}")


class UsageLimitExceeded(ConciergeAgentError):
    def __init__(self, limit_type, message=None):
        self.limit_type = limit_type
        super().__init__(message or f"usage limit exceeded: {limit_type}")
