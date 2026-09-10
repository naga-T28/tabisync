from ..content_data import (
    FAQ_SECTIONS,
    GUIDE_AI_CONCIERGE_FAQ,
    GUIDE_ALL_IN_ONE_FAQ,
    GUIDE_COLLABORATION_FAQ,
    GUIDE_NO_SIGNUP_FAQ,
    GUIDE_SAMPLE_FAQ,
)

"""AIコンシェルジュが「TabiSync自体の機能・使い方」を説明する際に検索対象とする一次データ。

公開ヘルプページ(guide/*, qa/)の本文を書き写すのではなく、既存content_data.pyの
FAQデータを再利用して二重管理を避ける(表示内容とAIの参照内容がずれないようにする)。
各エントリはconcierge_tools/help_tools.pyの軽量検索(文字bigram一致)の対象ドキュメント。
"""


def _faq_text(faq_items):
    return "\n".join(f"{item['question']} {item['answer']}" for item in faq_items)


APP_HELP_DOCUMENTS = [
    {
        "id": "guide_all_in_one",
        "title": "旅程・行きたい場所・持ち物・メモを一つにまとめる使い方",
        "url_name": "tabisync:guide_all_in_one",
        "summary": (
            "旅程表・行きたい場所・持ち物リスト・メモという4つの機能の役割分担、"
            "おすすめの入力順、登録できる件数の上限を説明するページ。"
        ),
        "search_text": (
            "旅程表 行きたい場所 持ち物リスト メモ 機能 使い分け 使い方 件数 上限 "
            "何ができる どんな機能がある TabiSyncの機能 "
            "旅程・行きたい場所・持ち物・メモを一つにまとめる使い方 "
            + _faq_text(GUIDE_ALL_IN_ONE_FAQ)
        ),
    },
    {
        "id": "guide_no_signup",
        "title": "登録不要で旅行しおりを作成・共有する方法",
        "url_name": "tabisync:guide_no_signup",
        "summary": (
            "アカウント登録なしでしおりを作成し、専用URLで共有できる仕組みと、"
            "閲覧用・編集用パスワードなど安全に使うためのポイントを説明するページ。"
        ),
        "search_text": (
            "登録不要 アカウント不要 ログイン不要 会員登録 URL共有 共有方法 パスワード "
            "安全に使う 無料 料金 "
            "登録なしで旅行しおりを作成・共有する方法 "
            + _faq_text(GUIDE_NO_SIGNUP_FAQ)
        ),
    },
    {
        "id": "guide_collaboration",
        "title": "友達・家族と旅行計画を共同編集する方法",
        "url_name": "tabisync:guide_collaboration",
        "summary": (
            "閲覧用パスワードと編集用パスワードの使い分け、共同編集の始め方、"
            "編集が重ならないためのコツを説明するページ。"
        ),
        "search_text": (
            "共同編集 みんなで編集 友達 家族 グループ 複数人 閲覧用パスワード 編集用パスワード "
            "権限 共有範囲 "
            "友達・家族と旅行計画を共同編集する方法 "
            + _faq_text(GUIDE_COLLABORATION_FAQ)
        ),
    },
    {
        "id": "guide_sample",
        "title": "旅行しおりのサンプルと作成手順",
        "url_name": "tabisync:guide_sample",
        "summary": (
            "完成済みのサンプルしおり(沖縄旅行3泊4日)の見方と、自分のしおりを作る4ステップ、"
            "登録できる件数の制限を説明するページ。"
        ),
        "search_text": (
            "サンプル デモ 見本 作り方 作成手順 初めて 使い方 チュートリアル しおりの作り方 "
            "旅行しおりのサンプルと作成手順 "
            + _faq_text(GUIDE_SAMPLE_FAQ)
        ),
    },
    {
        "id": "guide_ai_concierge",
        "title": "AIコンシェルジュを使った旅行計画の例と注意点",
        "url_name": "tabisync:guide_ai_concierge",
        "summary": (
            "AIコンシェルジュへの質問例、相談から提案の反映までの4ステップ、"
            "利用前に知っておくべき注意点を説明するページ。"
        ),
        "search_text": (
            "AIコンシェルジュ AI チャット 相談 質問例 何を聞けばいい 使い方 提案 反映 注意点 "
            "個人情報 利用回数 上限 "
            "AIコンシェルジュを使った旅行計画の例と注意点 "
            + _faq_text(GUIDE_AI_CONCIERGE_FAQ)
        ),
    },
]

for _section in FAQ_SECTIONS:
    APP_HELP_DOCUMENTS.append({
        "id": _section["id"],
        "title": _section["title"],
        "url_name": "tabisync:qa",
        "anchor": _section["id"],
        "summary": f"{_section['title']}に関するよくある質問。",
        "search_text": _section["title"] + " " + _faq_text(_section["questions"]),
    })
