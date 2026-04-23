from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tabisync", "0013_conciergechatlog"),
    ]

    operations = [
        migrations.AddField(
            model_name="itinerary",
            name="concierge_daily_limit",
            field=models.PositiveIntegerField(default=5),
        ),
    ]
