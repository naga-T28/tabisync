from django.db import transaction

from . import edit_actions

"""既存の編集適用ロジック(edit_actions.apply_edit_action)をDBセーブポイントでラップし、
検証だけを行ってDBを一切変更せず結果を返す。concierge_v2_apply_changes(実際の適用経路)と
完全に同じ検証結果を保証するため、専用のvalidate-onlyロジックを別実装しない。

トレードオフ: 自動採番IDに欠番が生じ得る(PostgreSQLのシーケンスはロールバックしても
巻き戻らない)。実害のない既知の特性として許容する。
"""


def propose_changes(run_context, actions):
    normalized = edit_actions.normalize_edit_actions(actions, max_items=12)
    if not normalized:
        return {"accepted": [], "rejected": []}

    accepted = []
    rejected = []

    with transaction.atomic():
        savepoint = transaction.savepoint()
        touched_schedule_days = set()
        for index, action in enumerate(normalized):
            try:
                result = edit_actions.apply_edit_action(run_context.itinerary, action, touched_schedule_days)
                accepted.append({**action, "preview_label": (result or {}).get("label", "")})
            except ValueError as exc:
                rejected.append({"index": index, "reason": str(exc)})
        transaction.savepoint_rollback(savepoint)

    return {"accepted": accepted, "rejected": rejected}
