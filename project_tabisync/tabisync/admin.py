from django.contrib import admin
from .models import Itinerary, TravelDate, Schedule, Memo, Item

admin.site.register(Itinerary)
admin.site.register(TravelDate)
admin.site.register(Schedule)
admin.site.register(Memo)
admin.site.register(Item)
