from django.db import migrations


GROUPS = (
    (
        "Autoimmune",
        "autoimmune",
        "Polycheck® panels for autoimmune screening and organ-related autoaggression.",
    ),
    (
        "Allergy",
        "allergy",
        "Polycheck® allergen-specific IgE panels for inhalation, food, paediatric and component testing.",
    ),
    (
        "Veterinary",
        "veterinary",
        "Polycheck® veterinary diagnostic panels customized for dogs, cats and horses.",
    ),
)


def create_polycheck_structure(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    ProductSubcategory = apps.get_model("catalog", "ProductSubcategory")
    Product = apps.get_model("catalog", "Product")
    Partner = apps.get_model("core", "Partner")

    category, _ = Category.objects.update_or_create(
        slug="polycheck",
        defaults={
            "name": "Polycheck",
            "menu_label": "Polycheck",
            "description": (
                "Polycheck® multiparameter in vitro diagnostic panels for allergy, "
                "autoimmune and veterinary testing."
            ),
            "icon": "test-tube",
            "display_order": 10,
            "is_active": True,
        },
    )
    for order, (name, slug, description) in enumerate(GROUPS):
        ProductSubcategory.objects.update_or_create(
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
        name="Polycheck",
        defaults={
            "country": "Germany",
            "website": "https://polycheck.de/alternative-products/",
            "description": (
                "German manufacturer of multiparameter in vitro diagnostic panels "
                "for allergy, autoimmune and veterinary testing."
            ),
            "equipment_group": "laboratory",
            "menu_label": "Polycheck",
            "menu_order": 2,
            "is_active": True,
        },
    )
    partner.menu_categories.set([category])
    Product.objects.filter(
        product_code="SL-EL-096",
        name="ELISA Microplate Reader ER-96",
        brand__iexact="Polycheck",
    ).update(is_active=False)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0013_product_source_image_productmedia_source_file"),
        ("core", "0010_alter_partner_menu_order"),
    ]

    operations = [
        migrations.RunPython(create_polycheck_structure, migrations.RunPython.noop),
    ]
