from django.db import migrations


def forward_migrate(apps, schema_editor):
    Event = apps.get_model("events", "Event")
    CallVersion = apps.get_model("events", "CallVersion")
    for event in Event.objects.all():
        if event.call_for_papers or event.bibliography:
            CallVersion.objects.create(
                event=event,
                language="fr",
                content=event.call_for_papers,
                bibliography=event.bibliography,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0008_callversion"),
    ]

    operations = [
        migrations.RunPython(forward_migrate, migrations.RunPython.noop),
        migrations.RemoveField(model_name="event", name="call_for_papers"),
        migrations.RemoveField(model_name="event", name="bibliography"),
    ]
