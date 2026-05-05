from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tabisync", "0017_itinerary_want_to_go_limit"),
    ]

    operations = [
        migrations.AddField(
            model_name="itinerary",
            name="qr_code",
            field=models.ImageField(blank=True, upload_to="qr_codes/"),
        ),
    ]
