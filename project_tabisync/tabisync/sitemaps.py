from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'monthly'

    def items(self):
        return ['tabisync:home', 'tabisync:create', 'tabisync:user_agreement', 'tabisync:privacy_policy', 'tabisync:contact','tabisync:qa','tabisync:profile']

    def location(self, item):
        return reverse(item)

