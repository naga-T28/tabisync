from django.shortcuts import render
from django.views.generic import TemplateView #add_2025.06.07

# ホーム画面を表示するビュー
class HomeView(TemplateView):
    template_name = "home.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context  
# 利用規約
class UserAgreementView(TemplateView):
    template_name = "user_agreement.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
# プライバシーポリシー
class PrivacyPolicyView(TemplateView):
    template_name = "privacy_policy.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    
class CreateView(TemplateView):
    template_name = "create.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    