from django.db import migrations


MICROSCOPE_PRODUCTS = (
    (
        "Stemi 355",
        "stemi-355",
        "ZEISS-STEMI-355",
        "Compact ZEISS stereo microscope family for routine observation and education.",
    ),
    (
        "SteREO Discovery.V8",
        "stereo-discovery-v8",
        "ZEISS-DISCOVERY-V8",
        "ZEISS stereo microscope family for detailed laboratory inspection and documentation.",
    ),
    (
        "SteREO Discovery.V12",
        "stereo-discovery-v12",
        "ZEISS-DISCOVERY-V12",
        "Advanced ZEISS stereo microscope family for demanding laboratory applications.",
    ),
    (
        "SteREO Discovery.V20",
        "stereo-discovery-v20",
        "ZEISS-DISCOVERY-V20",
        "High-performance ZEISS stereo microscope family for precise visual analysis.",
    ),
)


def add_light_microscopes(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")

    category, _ = Category.objects.update_or_create(
        slug="light-microscopes",
        defaults={
            "name": "Light Microscopes",
            "description": (
                "ZEISS stereo and light microscopy solutions for laboratory, "
                "research and educational applications."
            ),
            "icon": "microscope",
            "display_order": 10,
            "is_active": True,
        },
    )

    for name, slug, product_code, short_description in MICROSCOPE_PRODUCTS:
        Product.objects.update_or_create(
            product_code=product_code,
            defaults={
                "category": category,
                "name": name,
                "slug": slug,
                "brand": "ZEISS",
                "short_description": short_description,
                "description": (
                    f"{name} is part of the ZEISS stereo microscopy portfolio. "
                    "Contact Somlab for configuration, availability and application guidance."
                ),
                "specifications": "",
                "price": None,
                "availability": "on_request",
                "is_featured": False,
                "is_active": True,
            },
        )


def remove_light_microscopes(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    Category = apps.get_model("catalog", "Category")
    Product.objects.filter(
        product_code__in=[item[2] for item in MICROSCOPE_PRODUCTS]
    ).delete()
    Category.objects.filter(slug="light-microscopes").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_light_microscopes, remove_light_microscopes),
    ]
