from django.contrib import admin
from .models import (
    Itinerary, TravelDate, Schedule, Memo, Item, WantToGo, MemoV2, ScheduleV2,
    ConciergeChatLog, ConciergeToolCallLog, SiteAnnouncement,
)

admin.site.register(Itinerary)
admin.site.register(TravelDate)
admin.site.register(Schedule)
admin.site.register(ScheduleV2)
admin.site.register(Memo)
admin.site.register(Item)
admin.site.register(WantToGo)
admin.site.register(MemoV2)
admin.site.register(ConciergeChatLog)
admin.site.register(ConciergeToolCallLog)


@admin.register(SiteAnnouncement)
class SiteAnnouncementAdmin(admin.ModelAdmin):
    list_display = (
        "title", "level", "is_active", "show_on_home",
        "show_on_all_itineraries", "starts_at", "ends_at", "updated_at",
    )
    list_filter = ("level", "is_active", "show_on_home", "show_on_all_itineraries")
    search_fields = ("title", "message")
    filter_horizontal = ("itineraries",)
    readonly_fields = ("created_at", "updated_at")
