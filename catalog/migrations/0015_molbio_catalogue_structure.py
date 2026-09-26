from django.db import migrations


GROUPS = (
    ("Truenat Platform", "truenat-platform", "Portable sample preparation and real-time micro-PCR instruments."),
    ("Truenat Assays", "truenat-assays", "Chip-based real-time PCR assays across the official Truenat diagnostic portfolio."),
    ("iBreastExam", "ibreastexam", "Point-of-care, non-invasive breast health screening."),
    ("ProRad Atlas", "prorad-atlas", "Ultra-portable point-of-care digital X-ray imaging."),
    ("OptraScan", "optrascan", "Whole-slide scanners and digital pathology workflows."),
)


def create_molbio_structure(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    ProductSubcategory = apps.get_model("catalog", "ProductSubcategory")
    Partner = apps.get_model("core", "Partner")

    category, _ = Category.objects.update_or_create(
        slug="molbio",
        defaults={
            "name": "Molbio",
            "menu_label": "Molbio",
            "description": (
                "Molbio Diagnostics point-of-care molecular diagnostics, "
                "screening, portable radiology and digital pathology solutions."
            ),
            "icon": "test-tube",
            "display_order": 11,
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
        name="Molbio Diagnostics",
        defaults={
            "country": "India",
            "website": "https://www.molbiodiagnostics.com",
            "description": (
                "Diagnostics manufacturer developing portable molecular testing, "
                "screening and imaging solutions for decentralized healthcare."
            ),
            "equipment_group": "laboratory",
            "menu_label": "Molbio",
            "menu_order": 3,
            "is_active": True,
        },
    )
    partner.menu_categories.set([category])


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0014_polycheck_catalogue_structure"),
        ("core", "0010_alter_partner_menu_order"),
    ]

    operations = [
        migrations.RunPython(create_molbio_structure, migrations.RunPython.noop),
    ]
