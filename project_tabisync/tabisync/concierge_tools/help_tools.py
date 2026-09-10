import math
import re
from collections import Counter

from django.conf import settings
from django.urls import reverse

from ..concierge_agent.app_help_docs import APP_HELP_DOCUMENTS
from ..concierge_agent.errors import ToolExecutionError

"""TabiSync自体の機能・使い方を説明するためのRAG的な軽量検索Tool。

専用の埋め込みモデルやベクトルDBは持たず、文字bigramのTF-IDF風の重み付き一致度で
スコアリングする(日本語は単語間にスペースがなく、標準ライブラリのみで完結する手法として
bigram Overlapを採用)。単純な重なり数だけだと「は」「です」のような助詞・語尾がほぼ全
ドキュメントに出現し、無関係な質問でも上位に紛れ込むため、他ドキュメントに出現しにくい
bigramほど重みを大きくするIDF風の重みで割り引く。検索対象はconcierge_agent/app_help_docs.py
の静的な一次データのみで、しおりの中身(旅程・行きたい場所・持ち物・メモ)は含まない。
"""

MAX_RESULTS = 3
MIN_SCORE = 0.22


def _char_bigrams(text):
    normalized = re.sub(r"\s+", "", text or "")
    if len(normalized) < 2:
        return [normalized] if normalized else []
    return [normalized[i:i + 2] for i in range(len(normalized) - 1)]


_DOC_BIGRAM_COUNTS = [Counter(_char_bigrams(doc["search_text"])) for doc in APP_HELP_DOCUMENTS]
_DOC_COUNT = len(APP_HELP_DOCUMENTS)
_BIGRAM_DOC_FREQ = Counter()
for _counts in _DOC_BIGRAM_COUNTS:
    _BIGRAM_DOC_FREQ.update(_counts.keys())


def _idf(bigram):
    # 平滑化付きIDF: 全ドキュメントに出現するbigramでも重みが0にならないようにする。
    doc_freq = _BIGRAM_DOC_FREQ.get(bigram, 0)
    return math.log((_DOC_COUNT + 1) / (doc_freq + 1)) + 1.0


def _score(query_bigram_counts, doc_bigram_counts):
    """クエリのbigramがどれだけ重み付きでdocに含まれるか(重み付きcontainment)。"""
    if not query_bigram_counts or not doc_bigram_counts:
        return 0.0
    numerator = 0.0
    denominator = 0.0
    for bigram, q_count in query_bigram_counts.items():
        weight = _idf(bigram)
        denominator += weight * q_count
        numerator += weight * min(q_count, doc_bigram_counts.get(bigram, 0))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _build_url(doc):
    path = reverse(doc["url_name"])
    url = f"{settings.PUBLIC_BASE_URL}{path}"
    anchor = doc.get("anchor")
    if anchor:
        url += f"#{anchor}"
    return url


def search_app_help(run_context, query):
    """質問に近いTabiSyncのヘルプページ(使い方ガイド・FAQ)を検索する。
    戻り値は (tool_result, citations) のタプル。citationsはagent.py側で
    参照リンク(参照リンクチップ)としてそのまま使える{title, url}のリスト。"""
    query = (query or "").strip()
    if not query:
        raise ToolExecutionError("search_app_help", "invalid_query", "検索キーワードが空です。")

    query_bigram_counts = Counter(_char_bigrams(query))
    scored = []
    for doc, doc_bigram_counts in zip(APP_HELP_DOCUMENTS, _DOC_BIGRAM_COUNTS):
        score = _score(query_bigram_counts, doc_bigram_counts)
        if score >= MIN_SCORE:
            scored.append((score, doc))
    scored.sort(key=lambda pair: pair[0], reverse=True)

    results = [
        {"title": doc["title"], "summary": doc["summary"], "url": _build_url(doc)}
        for _score_value, doc in scored[:MAX_RESULTS]
    ]

    tool_result = {"results": results}
    citations = [{"title": item["title"], "url": item["url"]} for item in results]
    return tool_result, citations
