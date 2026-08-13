from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from django.views.generic import TemplateView

from ..content_data import FAQ_SECTIONS, iter_faq_questions
from ..seo import dumps_json_ld


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
        context["faq_sections"] = FAQ_SECTIONS
        context["faq_json_ld"] = dumps_json_ld({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": item["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": item["answer"],
                    },
                }
                for item in iter_faq_questions()
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

