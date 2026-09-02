from ..models import ConciergeToolCallLog


def summarize_tool_args(tool_id, args):
    """UsageEvent/ログへ保存してよい要約のみを返す。住所全文・メモ本文などの個人情報は含めない。"""
    args = args or {}
    if tool_id == "get_schedules":
        days = args.get("days")
        return {"days_count": len(days) if isinstance(days, list) else 0}
    if tool_id == "propose_changes":
        actions = args.get("actions") or []
        action_types = [a.get("action") for a in actions if isinstance(a, dict)]
        return {"action_types": action_types, "count": len(actions)}
    if tool_id == "show_map":
        ids = args.get("want_to_go_ids") or []
        return {"count": len(ids) if isinstance(ids, list) else 0}
    return {}


class RunTrace:
    """Agent run 1回分の実行記録。永続化はrunの終了時にpersist()でまとめて行う。"""

    def __init__(self, run_context):
        self.run_context = run_context
        self.selected_skill_ids = []
        self.selection_reason = ""
        self.tool_call_records = []
        self.openai_call_count = 0
        self.web_search_call_count = 0

    def record_skill_selection(self, skill_ids, reason):
        self.selected_skill_ids = list(skill_ids)
        self.selection_reason = reason

    def record_openai_call(self):
        self.openai_call_count += 1

    def record_web_search_calls(self, count):
        if count:
            self.web_search_call_count += count

    def record_tool_call(self, sequence_index, tool_id, tool_version, status,
                          duration_ms, error_type="", args_summary=None):
        self.tool_call_records.append({
            "sequence_index": sequence_index,
            "tool_id": tool_id,
            "tool_version": tool_version,
            "status": status,
            "duration_ms": duration_ms,
            "error_type": error_type or "",
            "args_summary": args_summary or {},
        })

    def persist_tool_calls(self, reservation):
        """ConciergeChatLog本体の更新(engine/selected_skill_ids等)は呼び出し側が
        DailyRunUsageService.finalize()で一括して行う。ここではTool呼び出し単位の
        記録(ConciergeToolCallLog)のみを永続化する。"""
        if self.tool_call_records:
            ConciergeToolCallLog.objects.bulk_create([
                ConciergeToolCallLog(
                    run=reservation,
                    sequence_index=record["sequence_index"],
                    tool_id=record["tool_id"],
                    tool_version=record["tool_version"],
                    status=record["status"],
                    duration_ms=record["duration_ms"],
                    error_type=record["error_type"],
                    args_summary=record["args_summary"],
                )
                for record in self.tool_call_records
            ])
