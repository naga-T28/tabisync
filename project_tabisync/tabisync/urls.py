from django.urls import path
from . import views

app_name = "tabisync"  

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),#ホーム画面のパス
    path('create/', views.CreateView.as_view(), name='create'),
    path('user_agreement/', views.UserAgreementView.as_view(), name='user_agreement'),
    path('privacy_policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
]

