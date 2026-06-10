import uuid

from django.db import migrations, models


def populate_blog_embed_tokens(apps, schema_editor):
    Itinerary = apps.get_model("tabisync", "Itinerary")
    for itinerary in Itinerary.objects.filter(blog_embed_token__isnull=True):
        itinerary.blog_embed_token = uuid.uuid4()
        itinerary.save(update_fields=["blog_embed_token"])


class Migration(migrations.Migration):

    dependencies = [
        ("tabisync", "0019_itinerary_cover_image_and_updated_on"),
    ]

    operations = [
        migrations.AddField(
            model_name="itinerary",
            name="blog_embed_token",
            field=models.UUIDField(default=None, editable=False, null=True),
        ),
        migrations.RunPython(populate_blog_embed_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="itinerary",
            name="blog_embed_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
