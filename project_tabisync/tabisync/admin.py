from django.contrib import admin
from .models import Itinerary, TravelDate, Schedule, Memo, Item,WantToGo,MemoV2,ScheduleV2

admin.site.register(Itinerary)
admin.site.register(TravelDate)
admin.site.register(Schedule)
admin.site.register(ScheduleV2)
admin.site.register(Memo)
admin.site.register(Item)
admin.site.register(WantToGo)
admin.site.register(MemoV2)
