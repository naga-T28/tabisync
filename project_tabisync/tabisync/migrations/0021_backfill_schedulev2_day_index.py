from django.db import migrations


def backfill_day_index(apps, schema_editor):
    # day_indexが未設定(NULL)の旧データを、しおりの開始日からの経過日数で補完する。
    # views/itinerary_helpers.py の get_schedule_day_index が使ってきたフォールバック
    # 計算式 (date - itinerary.start_date).days + 1 と同じロジック。
    ScheduleV2 = apps.get_model("tabisync", "ScheduleV2")

    for schedule in ScheduleV2.objects.filter(day_index__isnull=True).select_related("itinerary"):
        itinerary = schedule.itinerary
        if itinerary.start_date and schedule.date:
            computed = (schedule.date - itinerary.start_date).days + 1
        else:
            computed = 1
        schedule.day_index = max(1, computed)
        schedule.save(update_fields=["day_index"])


def noop_reverse(apps, schema_editor):
    # day_indexを再びNULLへ戻す意味のある逆操作はないため何もしない。
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tabisync', '0020_itinerary_blog_embed_token'),
    ]

    operations = [
        migrations.RunPython(backfill_day_index, noop_reverse),
    ]
