from django.db import migrations


REMOVED_CATEGORY_SLUGS = (
    "molecular-diagnostics",
    "laboratory-equipment",
    "laboratory-consumables",
    "diagnostics",
    "bioer",
    "biosan",
    "turklab",
    "geneproof",
)

REMOVED_PARTNERS = (
    "DIAGNOSTICS i.n.c.",
    "Bioer Technology",
    "Biosan",
    "Turklab",
    "GeneProof",
)


def remove_partner_catalogues(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    Partner = apps.get_model("core", "Partner")

    categories = Category.objects.filter(slug__in=REMOVED_CATEGORY_SLUGS)

    # Product.category is protected, so remove only the products owned by
    # these exact category records before deleting their subcategory trees.
    Product.objects.filter(category__in=categories).delete()
    categories.delete()

    # These five Partner rows were generated solely by the retired importer.
    # Preserve a row if it has since been configured for navigation or linked
    # to any category, because that would make it shared website data.
    Partner.objects.filter(
        name__in=REMOVED_PARTNERS,
        equipment_group="",
        menu_categories__isnull=True,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0022_partner_owned_catalogue_hierarchy"),
        ("core", "0010_alter_partner_menu_order"),
    ]

    operations = [
        migrations.RunPython(
            remove_partner_catalogues,
            migrations.RunPython.noop,
        ),
    ]
