from django.db import migrations


LABORATORY_MANUFACTURERS = (
    ("Beckman Coulter", "Beckman Coulter"),
    ("Polycheck", "Polycheck"),
    ("Molbio Diagnostics", "Molbio"),
    ("Medical Electronic Systems", "Medical Electronic System"),
    ("AMA Helic UBT Reader", "AMA Helic UBT Reader"),
    ("SD Biosensor", "SD Biosensor"),
    ("Eschweiler ABG", "Eschweiler ABG"),
)


def configure_product_navigation(apps, schema_editor):
    Partner = apps.get_model("core", "Partner")
    Category = apps.get_model("catalog", "Category")

    Partner.objects.update(equipment_group="", menu_label="", menu_order=0)

    configured = {}
    for menu_order, (name, menu_label) in enumerate(LABORATORY_MANUFACTURERS):
        partner, _ = Partner.objects.update_or_create(
            name=name,
            defaults={
                "menu_label": menu_label,
                "equipment_group": "laboratory",
                "menu_order": menu_order,
                "is_active": True,
            },
        )
        configured[name] = partner

    zeiss, _ = Partner.objects.update_or_create(
        name="ZEISS",
        defaults={
            "country": "Germany",
            "menu_label": "ZEISS Microscopy",
            "equipment_group": "medical",
            "menu_order": 0,
            "is_active": True,
        },
    )
    vatech, _ = Partner.objects.update_or_create(
        name="Vatech Dental",
        defaults={
            "menu_label": "Vatech Dental — All Products",
            "equipment_group": "dental",
            "menu_order": 0,
            "is_active": True,
        },
    )

    laboratory_categories = Category.objects.filter(slug__in=(
        "chemistry", "immunoassay", "hematology", "urinalysis",
        "microbiology", "blood-banking",
    ))
    configured["Beckman Coulter"].menu_categories.set(laboratory_categories)

    light_microscopes = Category.objects.filter(slug="light-microscopes")
    light_microscopes.update(menu_label="ZEISS Light Microscope")
    zeiss.menu_categories.set(light_microscopes)
    vatech.menu_categories.clear()


def clear_product_navigation(apps, schema_editor):
    Partner = apps.get_model("core", "Partner")
    Category = apps.get_model("catalog", "Category")
    Partner.objects.update(equipment_group="", menu_label="", menu_order=0)
    Category.objects.update(menu_label="")


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0007_category_menu_label"),
        ("core", "0008_partner_equipment_group_partner_menu_categories_and_more"),
    ]

    operations = [
        migrations.RunPython(
            configure_product_navigation,
            clear_product_navigation,
        ),
    ]
