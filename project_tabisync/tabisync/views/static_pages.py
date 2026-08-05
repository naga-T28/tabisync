from django.views.generic import TemplateView


# =========================
# 静的ページ・案内ページ
# =========================
class HomeView(TemplateView):
    template_name = "home.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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

