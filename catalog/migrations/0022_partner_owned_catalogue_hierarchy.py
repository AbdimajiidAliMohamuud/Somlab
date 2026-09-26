from django.db import migrations
from django.utils.text import slugify


PARTNER_CATEGORIES = (
    (
        "DIAGNOSTICS i.n.c.", "DIAGNOSTICS", "diagnostics",
        "Official DIAGNOSTICS microbiology identification, screening and susceptibility-testing products.",
        "test-tube", 103,
    ),
    (
        "Bioer Technology", "Bioer", "bioer",
        "Official Bioer molecular diagnostics, laboratory instruments and consumables.",
        "dna", 104,
    ),
    (
        "Biosan", "Biosan", "biosan",
        "Official Biosan laboratory instruments and life-science equipment.",
        "microscope", 105,
    ),
    (
        "Turklab", "TURKLAB", "turklab",
        "Official TURKLAB rapid diagnostic and blood-grouping products.",
        "test-tube", 106,
    ),
    (
        "GeneProof", "GeneProof", "geneproof",
        "Official GeneProof molecular diagnostic assays, extraction products and systems.",
        "dna", 107,
    ),
)


def move_products_to_partner_categories(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    ProductSubcategory = apps.get_model("catalog", "ProductSubcategory")

    for brand, name, slug, description, icon, order in PARTNER_CATEGORIES:
        category, _ = Category.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": description,
                "icon": icon,
                "display_order": order,
                "is_active": True,
            },
        )
        subcategories = {}
        products = Product.objects.filter(brand__iexact=brand).select_related(
            "subcategory"
        ).order_by("subcategory__display_order", "subcategory__name", "pk")
        for product in products:
            old_subcategory = product.subcategory
            if old_subcategory is None:
                product.category = category
                product.save(update_fields=["category"])
                continue
            key = old_subcategory.name.casefold()
            if key not in subcategories:
                subcategory, _ = ProductSubcategory.objects.update_or_create(
                    category=category,
                    slug=slugify(old_subcategory.name)[:80],
                    defaults={
                        "name": old_subcategory.name,
                        "description": old_subcategory.description,
                        "display_order": len(subcategories),
                        "is_active": True,
                    },
                )
                subcategories[key] = subcategory
            product.category = category
            product.subcategory = subcategories[key]
            product.save(update_fields=["category", "subcategory"])


class Migration(migrations.Migration):
    dependencies = [("catalog", "0021_partner_catalogue_categories")]

    operations = [
        migrations.RunPython(
            move_products_to_partner_categories,
            migrations.RunPython.noop,
        ),
    ]
