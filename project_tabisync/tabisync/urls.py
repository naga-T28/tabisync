from django.urls import path
from . import views

app_name = "tabisync"  

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),#ホーム画面のパス
    path('create/', views.CreateView.as_view(), name='create'),
    path('user_agreement/', views.UserAgreementView.as_view(), name='user_agreement'),
    path('privacy_policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('demo/', views.DemoContentView.as_view(), name='demo_content'),
    path('demo/edit', views.DemoEditView.as_view(), name='demo_edit'),
    path('demo/list', views.DemoListView.as_view(), name='demo_list'),
    path('demo/memo', views.DemoMemoView.as_view(), name='demo_memo'),
    path('updates/',views.UpdatesView.as_view(), name='updates'),
    path('content/<int:pk>/<uuid:token>/', views.ItineraryDetailView.as_view(), name='content'),
    path('content/<int:pk>/<uuid:token>/memo/', views.MemoDetailView.as_view(), name='content_memo'),
    path('content/<int:pk>/<uuid:token>/list/', views.ListDetailView.as_view(), name='content_list'),
    path('content/<int:pk>/<uuid:token>/password/', views.ItineraryPasswordView.as_view(), name='content_password'),
]

