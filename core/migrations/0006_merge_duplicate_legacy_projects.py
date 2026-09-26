from django.db import migrations


def merge_duplicate_legacy_projects(apps, schema_editor):
    CustomerProject = apps.get_model("core", "CustomerProject")
    CustomerProjectMedia = apps.get_model("core", "CustomerProjectMedia")

    customer_ids = CustomerProject.objects.filter(
        title="Completed work"
    ).order_by().values_list("customer_id", flat=True).distinct()

    for customer_id in customer_ids:
        projects = list(CustomerProject.objects.filter(
            customer_id=customer_id,
            title="Completed work",
        ).order_by("id"))
        if len(projects) < 2:
            continue
        primary = projects[0]
        existing_media = set(CustomerProjectMedia.objects.filter(
            project_id=primary.pk
        ).values_list("file", "media_type", "display_order"))
        for duplicate in projects[1:]:
            for item in CustomerProjectMedia.objects.filter(project_id=duplicate.pk):
                identity = (item.file.name, item.media_type, item.display_order)
                if identity in existing_media:
                    item.delete()
                else:
                    item.project_id = primary.pk
                    item.save(update_fields=["project"])
                    existing_media.add(identity)
            duplicate.delete()


class Migration(migrations.Migration):

    dependencies = [("core", "0005_customer_case_studies")]

    operations = [
        migrations.RunPython(
            merge_duplicate_legacy_projects,
            migrations.RunPython.noop,
        ),
    ]
