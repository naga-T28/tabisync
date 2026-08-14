from django.conf import settings


class NonProductionNoIndexMiddleware:
    """本番以外の全レスポンスを検索インデックスから除外する。"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not settings.IS_PRODUCTION:
            response["X-Robots-Tag"] = "noindex, nofollow"
        return response
