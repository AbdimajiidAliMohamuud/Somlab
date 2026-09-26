from django.db import migrations


def reconcile_zeiss(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    ProductSubcategory = apps.get_model("catalog", "ProductSubcategory")
    Partner = apps.get_model("core", "Partner")

    category = Category.objects.get(slug="light-microscopes")
    category.name = "ZEISS Light Microscopes"
    category.menu_label = "ZEISS Light Microscopes"
    category.is_active = True
    category.save(update_fields=["name", "menu_label", "is_active"])

    stereo = ProductSubcategory.objects.get(
        category=category,
        slug="stereo-and-zoom-microscopes",
    )
    stereo.name = "Stereo & Zoom Microscopes"
    stereo.save(update_fields=["name"])
    widefield = ProductSubcategory.objects.get(
        category=category,
        slug="widefield-microscopes",
    )

    Product.objects.update_or_create(
        product_code="ZEISS-LM-WF-019",
        defaults={
            "category": category,
            "subcategory": widefield,
            "name": "ZEISS Axiovert for Materials",
            "slug": "zeiss-axiovert-materials",
            "brand": "ZEISS",
            "short_description": (
                "Inverted microscopes for materials laboratories and smart "
                "digital documentation."
            ),
            "description": (
                "ZEISS Axiovert supports high-quality imaging of large and "
                "heavy materials samples using reflected or transmitted "
                "light. Axiovert 5 supports standalone smart documentation, "
                "while Axiovert 7 adds motorized workflow automation."
            ),
            "specifications": (
                "Format: Inverted widefield microscope\n"
                "Application: Materials laboratory and materialography\n"
                "Contrast methods: Reflected and transmitted light\n"
                "Models: Axiovert 5 and Axiovert 7\n"
                "Documentation: Standalone operation available with Axiovert 5\n"
                "Automation: Motorized Z-focus and XY stage available with Axiovert 7"
            ),
            "price": None,
            "availability": "on_request",
            "is_featured": False,
            "is_active": True,
        },
    )

    partner = Partner.objects.get(name="ZEISS")
    partner.menu_label = "ZEISS Microscopy"
    partner.equipment_group = "medical"
    partner.is_active = True
    partner.save(update_fields=[
        "menu_label", "equipment_group", "is_active",
    ])
    partner.menu_categories.set([category])


class Migration(migrations.Migration):
    dependencies = [("catalog", "0009_helic_abt_reader")]

    operations = [
        migrations.RunPython(reconcile_zeiss, migrations.RunPython.noop),
    ]
