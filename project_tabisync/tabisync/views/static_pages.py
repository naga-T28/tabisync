from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from django.views.generic import TemplateView

from ..content_data import (
    FAQ_SECTIONS,
    GUIDE_AI_CONCIERGE_FAQ,
    GUIDE_ALL_IN_ONE_FAQ,
    GUIDE_COLLABORATION_FAQ,
    GUIDE_NO_SIGNUP_FAQ,
    GUIDE_SAMPLE_FAQ,
    iter_faq_questions,
)
from ..seo import build_breadcrumb_list, build_faq_page, dumps_json_ld


# 実在する公式アカウント・サイトのみを列挙する。SNSアカウントを増減する際はここを更新する。
OFFICIAL_SAME_AS = [
    "https://blog.tabisync.com",
    "https://x.com/tabisync_com",
]


# =========================
# 静的ページ・案内ページ
# =========================
class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        home_url = f"{settings.PUBLIC_BASE_URL}{reverse('tabisync:home')}"

        organization = {
            "@type": "Organization",
            "@id": f"{home_url}#organization",
            "name": "TabiSync",
            "url": home_url,
            "logo": f"{settings.PUBLIC_BASE_URL}{static('img/icon-pc.webp')}",
            "sameAs": OFFICIAL_SAME_AS,
        }

        context["home_json_ld"] = dumps_json_ld({
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "WebSite",
                    "@id": f"{home_url}#website",
                    "name": "TabiSync",
                    "url": home_url,
                    "publisher": {"@id": organization["@id"]},
                },
                organization,
                {
                    "@type": "SoftwareApplication",
                    "name": "TabiSync",
                    "applicationCategory": "TravelApplication",
                    "operatingSystem": "Web",
                    "url": home_url,
                    "description": "ログインなしで旅程、行きたい場所、持ち物、メモをURL共有できる旅行しおりサービスです。",
                    "offers": {
                        "@type": "Offer",
                        "price": "0",
                        "priceCurrency": "JPY",
                    },
                    "featureList": [
                        "旅行しおりの作成",
                        "旅程のURL共有",
                        "行きたい場所の共有",
                        "持ち物リスト",
                        "AIコンシェルジュ",
                    ],
                    "publisher": {"@id": organization["@id"]},
                },
            ],
        })
        return context



# ホーム画面を表示するビュー
class ProfileView(TemplateView):
    template_name = "docs/profile.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context  



# 利用規約
class UserAgreementView(TemplateView):
    template_name = "docs/user_agreement.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context



class ConciergeTermsView(TemplateView):
    template_name = "docs/concierge_terms.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context



# Q and Aを表示するビュー
class QAView(TemplateView):
    template_name = "docs/qanda.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        home_url = f"{settings.PUBLIC_BASE_URL}{reverse('tabisync:home')}"
        page_url = f"{settings.PUBLIC_BASE_URL}{reverse('tabisync:qa')}"
        breadcrumb_items = [("ホーム", home_url), ("よくある質問", page_url)]
        faq_items = list(iter_faq_questions())

        context["faq_sections"] = FAQ_SECTIONS
        context["breadcrumb_items"] = breadcrumb_items
        context["faq_json_ld"] = dumps_json_ld({
            "@context": "https://schema.org",
            "@graph": [
                build_breadcrumb_list(breadcrumb_items),
                build_faq_page(faq_items),
            ],
        })
        return context



# プライバシーポリシー
class PrivacyPolicyView(TemplateView):
    template_name = "docs/privacy_policy.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context



class UpdatesView(TemplateView):
    template_name = "docs/update.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context



# =========================
# 検索意図別の説明・活用ページ
# =========================
# パンくず表示とBreadcrumbList JSON-LD、FAQ表示とFAQPage JSON-LDをそれぞれ同じ
# データから生成するための共通処理。ページごとのURL名・タイトル・FAQデータだけを
# 差し替えれば、表示と構造化データがずれずに新規ページを追加できる。
def _build_guide_page_context(url_name, page_title, faq_items):
    home_url = f"{settings.PUBLIC_BASE_URL}{reverse('tabisync:home')}"
    page_url = f"{settings.PUBLIC_BASE_URL}{reverse(url_name)}"
    breadcrumb_items = [("ホーム", home_url), (page_title, page_url)]
    return {
        "breadcrumb_items": breadcrumb_items,
        "faq_items": faq_items,
        "guide_json_ld": dumps_json_ld({
            "@context": "https://schema.org",
            "@graph": [
                build_breadcrumb_list(breadcrumb_items),
                build_faq_page(faq_items),
            ],
        }),
    }


class GuideSampleView(TemplateView):
    template_name = "docs/guide_sample.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_build_guide_page_context(
            "tabisync:guide_sample", "旅行しおりのサンプルと作成手順", GUIDE_SAMPLE_FAQ,
        ))
        return context



class GuideNoSignupView(TemplateView):
    template_name = "docs/guide_no_signup.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_build_guide_page_context(
            "tabisync:guide_no_signup", "登録不要で旅行しおりを作成・共有する方法", GUIDE_NO_SIGNUP_FAQ,
        ))
        return context



class GuideCollaborationView(TemplateView):
    template_name = "docs/guide_collaboration.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_build_guide_page_context(
            "tabisync:guide_collaboration", "友達・家族と旅行計画を共同編集する方法", GUIDE_COLLABORATION_FAQ,
        ))
        return context



class GuideAllInOneView(TemplateView):
    template_name = "docs/guide_all_in_one.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_build_guide_page_context(
            "tabisync:guide_all_in_one", "旅程・行きたい場所・持ち物・メモを一つにまとめる使い方", GUIDE_ALL_IN_ONE_FAQ,
        ))
        return context



class GuideAiConciergeView(TemplateView):
    template_name = "docs/guide_ai_concierge.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_build_guide_page_context(
            "tabisync:guide_ai_concierge", "AIコンシェルジュを使った旅行計画の例と注意点", GUIDE_AI_CONCIERGE_FAQ,
        ))
        return context
