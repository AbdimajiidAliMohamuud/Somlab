from django.db import migrations


def create_sd_biosensor_structure(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    ProductSubcategory = apps.get_model("catalog", "ProductSubcategory")
    Partner = apps.get_model("core", "Partner")

    category, _ = Category.objects.update_or_create(
        slug="sd-biosensor",
        defaults={
            "name": "SD Biosensor Rapid Test",
            "menu_label": "SD Biosensor Rapid Test",
            "description": (
                "Selected STANDARD Q rapid diagnostic tests from SD BIOSENSOR "
                "for malaria, hepatitis and blood-borne infections."
            ),
            "icon": "test-tube",
            "display_order": 12,
            "is_active": True,
        },
    )
    ProductSubcategory.objects.update_or_create(
        category=category,
        slug="standard-q",
        defaults={
            "name": "STANDARD Q",
            "description": (
                "Rapid immunochromatographic tests selected from the official "
                "SD BIOSENSOR STANDARD Q range."
            ),
            "display_order": 0,
            "is_active": True,
        },
    )
    partner, _ = Partner.objects.update_or_create(
        name="SD Biosensor",
        defaults={
            "country": "South Korea",
            "website": "https://www.sdbiosensor.com",
            "description": (
                "Global in vitro diagnostics manufacturer supplying rapid, "
                "fluorescence, molecular and immunoassay systems."
            ),
            "equipment_group": "laboratory",
            "menu_label": "SD Biosensor",
            "menu_order": 5,
            "is_active": True,
        },
    )
    partner.menu_categories.set([category])


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0015_molbio_catalogue_structure"),
        ("core", "0010_alter_partner_menu_order"),
    ]

    operations = [
        migrations.RunPython(
            create_sd_biosensor_structure,
            migrations.RunPython.noop,
        ),
    ]
