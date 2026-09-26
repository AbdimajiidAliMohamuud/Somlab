from django.db import migrations


def rename_truenat_subcategory(apps, schema_editor):
    ProductSubcategory = apps.get_model("catalog", "ProductSubcategory")
    ProductSubcategory.objects.filter(
        category__slug="molbio",
        slug="truenat-platform",
    ).update(name="Truenat")


def restore_truenat_platform_name(apps, schema_editor):
    ProductSubcategory = apps.get_model("catalog", "ProductSubcategory")
    ProductSubcategory.objects.filter(
        category__slug="molbio",
        slug="truenat-platform",
    ).update(name="Truenat Platform")


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0025_productrelateditem_image"),
    ]

    operations = [
        migrations.RunPython(
            rename_truenat_subcategory,
            restore_truenat_platform_name,
        ),
    ]
