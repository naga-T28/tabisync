from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.urls import reverse
from django.views.generic import TemplateView #add_2025.06.07
from django.views import View
from .models import Itinerary, TravelDate, Schedule, Memo, Item

# ホーム画面を表示するビュー
class HomeView(TemplateView):
    template_name = "home.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context  
# 利用規約
class UserAgreementView(TemplateView):
    template_name = "docs/user_agreement.html"
    
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

class DemoContentView(TemplateView):
    template_name = "demo/content_demo.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
class DemoMemoView(TemplateView):
    template_name = "demo/memo_demo.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    
class DemoEditView(TemplateView):
    template_name = "demo/edit_demo.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
class DemoListView(TemplateView):
    template_name = "demo/list_demo.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
#作成フォーム
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class CreateView(View):
    template_name = "tabisync/create.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        # 1. しおり本体の作成
        itinerary = Itinerary(
            title=request.POST.get('title'),
            subtitle=request.POST.get('subtitle'),
            description=request.POST.get('description'),
            reset_email=request.POST.get('reset_email', '')
        )
        itinerary.set_passwords(
            view_pw=request.POST.get('view_password', ''),
            edit_pw=request.POST.get('edit_password', '')
        )
        itinerary.save()

        # 2. 日付とスケジュール
        for i in range(100):
            date_key = f'dates[{i}][date]'
            if date_key not in request.POST:
                break
            travel_date = TravelDate.objects.create(
                itinerary=itinerary,
                date=request.POST[date_key],
                order=i
            )
            for j in range(100):
                prefix = f'dates[{i}][schedules][{j}]'
                if f'{prefix}[start_time]' not in request.POST:
                    break
                Schedule.objects.create(
                    travel_date=travel_date,
                    start_time=request.POST.get(f'{prefix}[start_time]', ''),
                    end_time=request.POST.get(f'{prefix}[end_time]', ''),
                    title=request.POST.get(f'{prefix}[title]', ''),
                    description=request.POST.get(f'{prefix}[description]', ''),
                    location=request.POST.get(f'{prefix}[location]', ''),
                    location_url=request.POST.get(f'{prefix}[location_url]', ''),
                    order=j
                )

        # 3. メモ
        for i in range(100):
            title_key = f'memos[{i}][title]'
            if title_key not in request.POST:
                break
            Memo.objects.create(
                itinerary=itinerary,
                title=request.POST.get(title_key, ''),
                content=request.POST.get(f'memos[{i}][content]', '')
            )

        # 4. 持ち物
        for i in range(100):
            title_key = f'items[{i}][title]'
            if title_key not in request.POST:
                break
            Item.objects.create(
                itinerary=itinerary,
                title=request.POST.get(title_key, ''),
                detail=request.POST.get(f'items[{i}][detail]', '')
            )

        return redirect(reverse('tabisync:content', kwargs={
            'pk': itinerary.pk,
            'token': itinerary.token
        }))
#個別ページ
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class ItineraryDetailView(TemplateView):
    template_name = "tabisync/content.html"

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")
        self.itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        if self.itinerary.view_password and not request.session.get(f'view_auth_{pk}_{token}', False):
            return redirect(reverse('tabisync:content_password', kwargs={'pk': pk, 'token': token}))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        itinerary = self.itinerary  # dispatch() で取得したものを使用
        travel_dates = itinerary.travel_dates.all().order_by('date')

        for travel_date in travel_dates:
            travel_date.sorted_schedules = travel_date.schedules.all().order_by('start_time')

        if travel_dates.exists():
            first_date = travel_dates.first().date
            last_date = travel_dates.last().date
            context["first_date_str"] = first_date.strftime('%Y.%m.%d')
            context["last_date_str"] = last_date.strftime('%Y.%m.%d')
        else:
            context["first_date_str"] = None
            context["last_date_str"] = None

        context["itinerary"] = itinerary
        context["travel_dates"] = travel_dates
        context["memos"] = itinerary.memos.all()
        context["items"] = itinerary.items.all()

        return context

#memoページ
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class MemoDetailView(TemplateView):
    template_name = "tabisync/memo.html"

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")
        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        # 閲覧用パスワードが設定されているかチェック
        if itinerary.view_password and not request.session.get(f'view_auth_{pk}_{token}', False):
            # 認証されていなければパスワード入力画面へリダイレクト
            return redirect(reverse('tabisync:content_password', kwargs={'pk': pk, 'token': token}))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")
        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        travel_dates = itinerary.travel_dates.all().order_by('date')

            # 最初と最後の日付を取得（存在する場合）
        if travel_dates.exists():
            first_date = travel_dates.first().date
            last_date = travel_dates.last().date

            # "2025.02.08" 形式にフォーマット（strftime使用）
            context["first_date_str"] = first_date.strftime('%Y.%m.%d')
            context["last_date_str"] = last_date.strftime('%Y.%m.%d')
        else:
            context["first_date_str"] = None
            context["last_date_str"] = None

        context["itinerary"] = itinerary
        context["travel_dates"] = itinerary.travel_dates.all()
        context["memos"] = itinerary.memos.all()
        context["items"] = itinerary.items.all()
        return context

#listページ
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class ListDetailView(TemplateView):
    template_name = "tabisync/list.html"

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")
        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        # 閲覧用パスワードが設定されているかチェック
        if itinerary.view_password and not request.session.get(f'view_auth_{pk}_{token}', False):
            # 認証されていなければパスワード入力画面へリダイレクト
            return redirect(reverse('tabisync:content_password', kwargs={'pk': pk, 'token': token}))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")
        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        travel_dates = itinerary.travel_dates.all().order_by('date')

        if travel_dates.exists():
            first_date = travel_dates.first().date
            last_date = travel_dates.last().date
            context["first_date_str"] = first_date.strftime('%Y.%m.%d')
            context["last_date_str"] = last_date.strftime('%Y.%m.%d')
        else:
            context["first_date_str"] = None
            context["last_date_str"] = None

        context["itinerary"] = itinerary
        context["travel_dates"] = travel_dates
        context["memos"] = itinerary.memos.all()
        
        items = itinerary.items.all()
        context["items"] = items

        # 全てのアイテムの title と detail が空かをチェック
        context["all_items_empty"] = all(
            not item.title and not item.detail for item in items
        )

        return context

    
#パスワード入力画面
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class ItineraryPasswordView(View):
    template_name = 'tabisync/password.html'

    def get(self, request, pk, token):
        return render(request, self.template_name, {'pk': pk, 'token': token})

    def post(self, request, pk, token):
        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)
        input_password = request.POST.get('view_password', '')

        if itinerary.check_view_password(input_password):
            # セッションに認証済みフラグをセット（キーは任意）
            request.session[f'view_auth_{pk}_{token}'] = True
            return redirect(reverse('tabisync:content', kwargs={'pk': pk, 'token': token}))
        else:
            context = {'error': 'パスワードが違います', 'pk': pk, 'token': token}
            return render(request, self.template_name, context)