from django.urls import path
from . import views

app_name = "tabisync"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),#ホーム画面のパス
    path('create/', views.CreateView.as_view(), name='create'),
    path('qa/', views.QAView.as_view(), name='qa'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('user_agreement/', views.UserAgreementView.as_view(), name='user_agreement'),
    path('privacy_policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('demo/', views.DemoContentView.as_view(), name='demo_content'),
    path('demo/edit', views.DemoEditView.as_view(), name='demo_edit'),
    path('demo/list', views.DemoListView.as_view(), name='demo_list'),
    path('demo/memo', views.DemoMemoView.as_view(), name='demo_memo'),
    path("contact/", views.ContactFormView.as_view(), name="contact"),
    path('updates/',views.UpdatesView.as_view(), name='updates'),
    path("offline/", views.offline_view, name="offline"),
    path("robots.txt", views.robots_txt_view, name="robots_txt"),
    path('content/<int:pk>/<uuid:token>/', views.ItineraryDetailView.as_view(), name='content'),
    path('content/<int:pk>/<uuid:token>/edit', views.EditView.as_view(), name='edit'),
    path('content/<int:pk>/<uuid:token>/memo/', views.MemoDetailView.as_view(), name='content_memo'),
    path('content/<int:pk>/<uuid:token>/list/', views.ListDetailView.as_view(), name='content_list'),
    path("reset-link/<int:pk>/<uuid:token>/<str:type>/",views.SendResetLinkView.as_view(),name="send_reset_link"),
    path("reset/<str:signed_token>/", views.ResetPasswordView.as_view(), name="reset_password"),
    path('content/<int:pk>/<uuid:token>/password/', views.ItineraryPasswordView.as_view(), name='content_password'),#下からv2
    path('content/v2/<int:pk>/<uuid:token>/', views.ItineraryDetailV2View.as_view(), name='content_v2'),
    path('content/v2/<int:pk>/<uuid:token>/edit/', views.EditMenuV2View.as_view(), name='content_edit_v2'),
    path('content/v2/<int:pk>/<uuid:token>/edit/content/', views.EditContentFormV2View.as_view(), name='content_edit_form_v2'),
    path('content/v2/<int:pk>/<uuid:token>/schedule/edit/', views.ScheduleV2EditView.as_view(), name='Scheduleedit'),
    path('content/v2/<int:pk>/<uuid:token>/want-to/edit/', views.WantToGoV2View.as_view(), name='Wantedit'),
    path('content/v2/<int:pk>/<uuid:token>/want-to/', views.WantToGoMapView.as_view(), name='Wantto'),
    path('content/v2/<int:pk>/<uuid:token>/memo/', views.MemoV2View.as_view(), name='V2_memo'),
    path('content/v2/<int:pk>/<uuid:token>/list/', views.ChecklistV2View.as_view(), name='V2_list'),
    path('content/v2/<int:pk>/<uuid:token>/concierge/', views.ConciergeV2View.as_view(), name='V2_concierge'),
    path('content/v2/<int:pk>/<uuid:token>/list/edit/', views.ChecklistV2EditView.as_view(), name='V2_list_edit'),
    path("content/v2/<int:pk>/<uuid:token>/schedule/row-save/",views.schedule_v2_row_save,name="schedule_v2_row_save"),
    path("content/v2/<int:pk>/<uuid:token>/schedule/row-delete/",views.schedule_v2_row_delete,name="schedule_v2_row_delete"),
]
