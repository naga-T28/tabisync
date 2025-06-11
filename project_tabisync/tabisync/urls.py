from django.urls import path
from . import views

app_name = "tabisync"  

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),#ホーム画面のパス
    path('create/', views.CreateView.as_view(), name='create'),
    path('user_agreement/', views.UserAgreementView.as_view(), name='user_agreement'),
    path('privacy_policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('updates/',views.UpdatesView.as_view(), name='updates'),
    path('content/<int:pk>/<uuid:token>/', views.ItineraryDetailView.as_view(), name='content'),
    path('content/<int:pk>/<uuid:token>/password/', views.ItineraryPasswordView.as_view(), name='content_password'),
]

