from django.db import migrations


PUBLIC_CATEGORIES = (
    (
        "Chemistry",
        "chemistry",
        "Analysers, reagents, calibrators and controls for routine chemistry.",
        "clinical-chemistry",
    ),
    (
        "Immunoassay",
        "immunoassay",
        "Immunoassay products for infectious disease, autoimmunity and routine diagnostics.",
        "immunoassays-elisa",
    ),
    (
        "Hematology",
        "hematology",
        "Hematology analysers, reagents and supporting laboratory products.",
        None,
    ),
    (
        "Urinalysis",
        "urinalysis",
        "Urinalysis analysers, test strips and supporting diagnostic products.",
        None,
    ),
    (
        "Microbiology",
        "microbiology",
        "Culture, susceptibility testing, ESR and microbiology laboratory equipment.",
        None,
    ),
    (
        "Blood Banking",
        "blood-banking",
        "Blood storage, grouping, separation and donor-care products.",
        None,
    ),
    (
        "Light Microscopes",
        "light-microscopes",
        "ZEISS stereo and light microscopy solutions for laboratory, research and education.",
        None,
    ),
)


def limit_public_categories(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")

    for display_order, (name, slug, description, legacy_slug) in enumerate(PUBLIC_CATEGORIES):
        category = Category.objects.filter(slug=slug).first()
        legacy = (
            Category.objects.filter(slug=legacy_slug).first()
            if legacy_slug
            else None
        )

        if category and legacy and category.pk != legacy.pk:
            Product.objects.filter(category=legacy).update(category=category)
            legacy.is_active = False
            legacy.save(update_fields=["is_active"])
        elif not category and legacy:
            category = legacy
            category.slug = slug

        if not category:
            category = Category(slug=slug)

        category.name = name
        category.description = description
        category.display_order = display_order
        category.is_active = True
        category.save()

    allowed_slugs = [item[1] for item in PUBLIC_CATEGORIES]
    Category.objects.exclude(slug__in=allowed_slugs).update(is_active=False)
    Product.objects.exclude(category__slug__in=allowed_slugs).update(
        is_active=False,
        is_featured=False,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_light_microscopes"),
    ]

    operations = [
        migrations.RunPython(limit_public_categories, migrations.RunPython.noop),
    ]
