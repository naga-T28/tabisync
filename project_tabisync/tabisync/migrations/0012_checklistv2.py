from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tabisync", "0011_schedulev2_day_index"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChecklistV2",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content", models.TextField(blank=True, default="[]")),
                ("itinerary", models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="checklist_v2", to="tabisync.itinerary")),
            ],
        ),
    ]
