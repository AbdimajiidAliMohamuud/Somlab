from django.db import migrations


def create_mes_sqa_structure(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    ProductSubcategory = apps.get_model("catalog", "ProductSubcategory")
    Partner = apps.get_model("core", "Partner")

    category, _ = Category.objects.update_or_create(
        slug="medical-electronic-systems",
        defaults={
            "name": "Semen Analyzers (SQA)",
            "menu_label": "Semen Analyzers (SQA)",
            "description": (
                "Medical Electronic Systems automated semen-analysis equipment "
                "for clinical and andrology laboratories."
            ),
            "icon": "microscope",
            "display_order": 13,
            "is_active": True,
        },
    )
    ProductSubcategory.objects.update_or_create(
        category=category,
        slug="automated-semen-analysis-solutions",
        defaults={
            "name": "Automated Semen Analysis Solutions",
            "description": (
                "MES automated semen-analysis systems for hospitals, fertility "
                "centres, reference laboratories and sperm banks."
            ),
            "display_order": 0,
            "is_active": True,
        },
    )
    partner, _ = Partner.objects.get_or_create(
        name="Medical Electronic Systems",
        defaults={
            "website": "https://mes-global.com/",
            "equipment_group": "laboratory",
            "menu_label": "Medical Electronic System",
            "menu_order": 3,
            "is_active": True,
        },
    )
    partner.menu_categories.add(category)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0016_sd_biosensor_standard_q"),
        ("core", "0010_alter_partner_menu_order"),
    ]

    operations = [
        migrations.RunPython(
            create_mes_sqa_structure,
            migrations.RunPython.noop,
        ),
    ]
