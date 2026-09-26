from django.db import migrations


def import_vatech_catalogue(apps, schema_editor):
    from catalog.management.commands.import_vatech_dental_products import (
        BRAND,
        OFFICIAL_CATALOGUE,
        VATECH_PRODUCTS,
    )

    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    ProductSubcategory = apps.get_model("catalog", "ProductSubcategory")
    Partner = apps.get_model("core", "Partner")

    category, _ = Category.objects.update_or_create(
        slug="vatech-dental",
        defaults={
            "name": BRAND,
            "menu_label": BRAND,
            "description": "Vatech dental imaging systems and intraoral imaging solutions.",
            "icon": "analyser",
            "display_order": 9,
            "is_active": True,
        },
    )
    groups = {}
    for order, (name, slug, description) in enumerate((
        ("3D Imaging", "3d-imaging", "CBCT and multi-modality dental imaging systems for three-dimensional diagnosis."),
        ("2D Imaging", "2d-imaging", "Panoramic and cephalometric dental imaging systems."),
        ("IOS and IOX", "ios-iox", "Intraoral X-ray generators and digital intraoral sensors."),
    )):
        groups[slug], _ = ProductSubcategory.objects.update_or_create(
            category=category,
            slug=slug,
            defaults={
                "name": name,
                "description": description,
                "display_order": order,
                "is_active": True,
            },
        )

    partner, _ = Partner.objects.update_or_create(
        name=BRAND,
        defaults={
            "country": "South Korea",
            "website": OFFICIAL_CATALOGUE,
            "equipment_group": "dental",
            "menu_label": BRAND,
            "menu_order": 8,
            "is_active": True,
        },
    )
    partner.menu_categories.set([category])

    for definition in VATECH_PRODUCTS:
        Product.objects.update_or_create(
            product_code=definition["product_code"],
            defaults={
                "category": category,
                "subcategory": groups[definition["group"]],
                "name": definition["name"],
                "slug": definition["slug"],
                "brand": BRAND,
                "short_description": definition["short_description"],
                "description": definition["description"],
                "specifications": definition["specifications"],
                "price": None,
                "availability": "on_request",
                "is_featured": False,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("catalog", "0010_reconcile_zeiss_light_microscopes")]

    operations = [
        migrations.RunPython(import_vatech_catalogue, migrations.RunPython.noop),
    ]
