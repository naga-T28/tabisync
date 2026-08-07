import os
import time
from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(frozen=True)
class RunContext:
    """Agent run 1回分のサーバー側コンテキスト。

    Toolハンドラはこれ経由でのみitineraryへアクセスする。pk/token/password/session key等の
    秘密値はここにも、Tool引数スキーマにも含めない(モデルが要求しようがない設計)。
    """

    itinerary: "tabisync.models.Itinerary"  # noqa: F821 (循環import回避のための文字列注釈)
    can_edit: bool
    conversation_id: UUID
    run_id: UUID = field(default_factory=uuid4)
    started_at: float = field(default_factory=time.monotonic)


def is_agent_mode_enabled(itinerary) -> bool:
    """Skill/Tool駆動のAgent経路を使うかどうかを判定する。

    CONCIERGE_AGENT_ENABLED_ITINERARY_IDS が設定されていれば、そこに含まれるpkのみ
    (内部QAや一部しおりだけの限定公開用)。未設定ならCONCIERGE_AGENT_ENABLEDの
    グローバル設定に従う。判定は必ずサーバー側リクエストごとに行い、結果をクライアントへ
    永続的な権限として渡さない。
    """
    allowlist = {
        value.strip()
        for value in os.environ.get("CONCIERGE_AGENT_ENABLED_ITINERARY_IDS", "").split(",")
        if value.strip()
    }
    if allowlist:
        return str(itinerary.pk) in allowlist
    return os.environ.get("CONCIERGE_AGENT_ENABLED", "false").strip().lower() == "true"
