from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("tabisync", "0012_checklistv2"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConciergeChatLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("conversation_id", models.UUIDField(db_index=True, default=uuid.uuid4)),
                ("turn_index", models.PositiveIntegerField(default=1)),
                ("user_message", models.TextField()),
                ("moderation_prompt", models.TextField(blank=True)),
                ("moderation_result", models.JSONField(blank=True, default=dict)),
                ("data_selection_prompt", models.TextField(blank=True)),
                ("data_selection_result", models.JSONField(blank=True, default=dict)),
                ("answer_prompt", models.TextField(blank=True)),
                ("answer_context", models.JSONField(blank=True, default=dict)),
                ("assistant_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "itinerary",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="concierge_logs", to="tabisync.itinerary"),
                ),
            ],
            options={
                "ordering": ["conversation_id", "turn_index", "id"],
            },
        ),
    ]
