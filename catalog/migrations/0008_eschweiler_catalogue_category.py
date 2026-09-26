from django.db import migrations


def create_eschweiler_catalogue(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    ProductSubcategory = apps.get_model("catalog", "ProductSubcategory")
    Product = apps.get_model("catalog", "Product")
    Partner = apps.get_model("core", "Partner")

    category, _ = Category.objects.update_or_create(
        slug="eschweiler-abg",
        defaults={
            "name": "Eschweiler ABG",
            "description": (
                "ESCHWEILER blood gas, electrolyte and metabolite analysers, "
                "system components and consumables."
            ),
            "icon": "analyser",
            "display_order": 7,
            "is_active": True,
        },
    )
    subcategories = {}
    for display_order, (name, slug, description) in enumerate((
        (
            "modular pro",
            "modular-pro",
            "The modular pro analyser family, measurement components, calibration and connectivity items.",
        ),
        (
            "combi line 2",
            "combi-line-2",
            "The combi line 2 analyser family, sensors, sample handling and calibration consumables.",
        ),
    )):
        subcategory, _ = ProductSubcategory.objects.update_or_create(
            category=category,
            slug=slug,
            defaults={
                "name": name,
                "description": description,
                "display_order": display_order,
                "is_active": True,
            },
        )
        subcategories[slug] = subcategory

    Product.objects.filter(product_code="ESCH-MODULAR-PRO").update(
        category=category,
        subcategory=subcategories["modular-pro"],
    )
    Product.objects.filter(product_code="ESCH-COMBI-LINE-2").update(
        category=category,
        subcategory=subcategories["combi-line-2"],
    )
    partner = Partner.objects.filter(name="Eschweiler ABG").first()
    if partner:
        partner.menu_categories.set([category])


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0007_category_menu_label"),
        ("core", "0010_alter_partner_menu_order"),
    ]

    operations = [
        migrations.RunPython(
            create_eschweiler_catalogue,
            migrations.RunPython.noop,
        ),
    ]
