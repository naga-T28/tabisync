from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'monthly'

    def items(self):
        return [
            'tabisync:home',
            'tabisync:create',
            'tabisync:qa',
            'tabisync:updates',
            'tabisync:profile',
            'tabisync:contact',
            'tabisync:user_agreement',
            'tabisync:concierge_terms',
            'tabisync:privacy_policy',
        ]

    def location(self, item):
        return reverse(item)
