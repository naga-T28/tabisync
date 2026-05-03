from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tabisync", "0016_alter_schedulev2_icon"),
    ]

    operations = [
        migrations.AddField(
            model_name="itinerary",
            name="want_to_go_limit",
            field=models.PositiveIntegerField(default=30),
        ),
    ]
