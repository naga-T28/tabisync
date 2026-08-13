import json

from django.core.serializers.json import DjangoJSONEncoder
from django.utils.safestring import mark_safe

# <script type="application/ld+json">の外へ値がエスケープするのを防ぐための変換。
# django.utils.html.json_scriptと同じ変換だが、あちらはtype="application/json"
# 固定でJSON-LDには使えないため、同じ安全性でtype="application/ld+json"を
# 自前で出力する。
_JSON_LD_ESCAPES = {
    ord(">"): "\\u003E",
    ord("<"): "\\u003C",
    ord("&"): "\\u0026",
}


def dumps_json_ld(data):
    """JSON-LD用の構造化データをテンプレートへ安全に埋め込める形へ変換する。

    文字列連結でスクリプトを組み立てず、json.dumpsの出力をエスケープしてから
    mark_safeする。呼び出し側は`<script type="application/ld+json">{{ value }}</script>`
    のようにそのまま出力すればよい。
    """
    json_str = json.dumps(data, cls=DjangoJSONEncoder, ensure_ascii=False)
    return mark_safe(json_str.translate(_JSON_LD_ESCAPES))
