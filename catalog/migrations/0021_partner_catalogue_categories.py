from django.db import migrations


CATEGORIES = (
    (
        "Molecular Diagnostics",
        "molecular-diagnostics",
        "PCR systems, molecular assays, extraction products and supporting reagents.",
        "dna",
        100,
    ),
    (
        "Laboratory Equipment",
        "laboratory-equipment",
        "General laboratory, sample-preparation, incubation and bioprocessing equipment.",
        "microscope",
        101,
    ),
    (
        "Laboratory Consumables",
        "laboratory-consumables",
        "Laboratory plastics, pipetting products and molecular-biology consumables.",
        "test-tube",
        102,
    ),
)


def create_categories(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    for name, slug, description, icon, order in CATEGORIES:
        Category.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": description,
                "icon": icon,
                "display_order": order,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("catalog", "0020_product_is_catalogue_listing")]

    operations = [
        migrations.RunPython(create_categories, migrations.RunPython.noop),
    ]
