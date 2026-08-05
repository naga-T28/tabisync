from django.views.generic import TemplateView


# =========================
# デモページ
# =========================
class DemoContentView(TemplateView):
    template_name = "demo/content_demo.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["demo_nav"] = "content"
        return context



class DemoMemoView(TemplateView):
    template_name = "demo/memo_demo.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["demo_nav"] = "memo"
        return context



class DemoEditView(TemplateView):
    template_name = "demo/edit_demo.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["demo_nav"] = "edit"
        return context



class DemoListView(TemplateView):
    template_name = "demo/list_demo.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["demo_nav"] = "list"
        return context



class DemoV2ContentView(TemplateView):
    template_name = "demo/v2_content_demo.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["demo_nav"] = "content"
        return context



class DemoV2MemoView(TemplateView):
    template_name = "demo/v2_memo_demo.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["demo_nav"] = "memo"
        return context



class DemoV2ListView(TemplateView):
    template_name = "demo/v2_list_demo.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["demo_nav"] = "list"
        return context



class DemoV2MapView(TemplateView):
    template_name = "demo/v2_map_demo.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["demo_nav"] = "map"
        return context



class DemoV2EditView(TemplateView):
    template_name = "demo/v2_edit_demo.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["demo_nav"] = "edit"
        return context



class DemoV2ConciergeView(TemplateView):
    template_name = "demo/v2_concierge_demo.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["demo_nav"] = "concierge"
        return context

