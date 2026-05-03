from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tabisync", "0014_itinerary_concierge_daily_limit"),
    ]

    operations = [
        migrations.AddField(
            model_name="schedulev2",
            name="icon",
            field=models.CharField(
                choices=[
                    ("default", "通常"),
                    ("food", "食事"),
                    ("move", "移動"),
                    ("photo", "観光"),
                    ("stay", "宿泊"),
                    ("shopping", "買い物"),
                    ("event", "イベント"),
                ],
                default="default",
                max_length=20,
            ),
        ),
    ]
