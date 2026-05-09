from django.db import migrations, models
import tabisync.models


class Migration(migrations.Migration):

    dependencies = [
        ("tabisync", "0018_itinerary_qr_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="itinerary",
            name="cover_image",
            field=models.ImageField(blank=True, upload_to=tabisync.models.itinerary_cover_upload_to),
        ),
        migrations.AddField(
            model_name="itinerary",
            name="cover_image_updated_on",
            field=models.DateField(blank=True, null=True),
        ),
    ]
