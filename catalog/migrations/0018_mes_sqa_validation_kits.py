from django.db import migrations


def create_mes_sqa_validation_kits(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    ProductSubcategory = apps.get_model("catalog", "ProductSubcategory")

    category = Category.objects.get(slug="medical-electronic-systems")
    ProductSubcategory.objects.update_or_create(
        category=category,
        slug="semen-analysis-validation-kits",
        defaults={
            "name": "Semen Analysis & Validation Kits",
            "description": (
                "Official MES testing, advanced-assessment, validation and SQA "
                "supplies directly supporting automated semen-analysis workflows."
            ),
            "display_order": 1,
            "is_active": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0017_mes_sqa_catalogue_structure"),
    ]

    operations = [
        migrations.RunPython(
            create_mes_sqa_validation_kits,
            migrations.RunPython.noop,
        ),
    ]
