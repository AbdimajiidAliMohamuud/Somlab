from django.db import migrations


PARTNERS = (
    {
        "name": "DIAGNOSTICS i.n.c.",
        "country": "Slovak",
        "description": (
            "DIAGNOSTICS i.n.c. is a Slovak company, which is engaged in "
            "research and development of medical devices in the field of "
            "microbiology from year 2010. We are focusing on the phenotypic "
            "identification of microorganisms, bacteria and yeasts."
        ),
        "website": "http://www.diagnostics.sk/?lang=en",
        "logo": "partners/diagnostics.png",
        "display_order": 0,
        "menu_order": 20,
    },
    {
        "name": "Bioer Technology",
        "country": "China",
        "description": (
            "Hangzhou Bioer Technology is a leading supplier of life science "
            "and medical diagnostic products in China, we specialize in the "
            "research and development, manufacture and sales of molecular "
            "detection serial products including instruments, reagents and "
            "consumables."
        ),
        "website": "https://en.bioer.com/",
        "logo": "partners/bioer-supplier-color.png",
        "display_order": 2,
        "menu_order": 21,
    },
    {
        "name": "Biosan",
        "country": "Latvia",
        "description": (
            "Biosan is a trusted manufacturer of laboratory equipment, "
            "delivering innovative and reliable solutions for life science "
            "research and sample preparation worldwide."
        ),
        "website": "https://biosan.lv/",
        "logo": "partners/Logo-Biosan-600x422.gif",
        "display_order": 4,
        "menu_order": 22,
    },
    {
        "name": "Turklab",
        "country": "Turkey",
        "description": (
            "Turklab continues its activities actively with its educated and "
            "creative R&D staff consisting of PhD biochemists, high "
            "biochemists, high bioengineers and microbiologists."
        ),
        "website": "https://www.turklab.com.tr/en",
        "logo": "partners/files_2022-12-09_16-15-27.jpg",
        "display_order": 6,
        "menu_order": 23,
    },
    {
        "name": "GeneProof",
        "country": "Czech Republic",
        "description": (
            "GeneProof is a biotechnology company operating in the field of "
            "molecular in vitro diagnostics of serious infections and genetic "
            "diseases. We develop, produce and distribute technologically "
            "advanced, high quality, user-friendly and affordable PCR products."
        ),
        "website": "https://www.geneproof.com/",
        "logo": "partners/GeneProof_logo.png",
        "display_order": 7,
        "menu_order": 24,
    },
)


def restore_partners(apps, schema_editor):
    Partner = apps.get_model("core", "Partner")

    for definition in PARTNERS:
        name = definition["name"]
        defaults = {
            key: value
            for key, value in definition.items()
            if key != "name"
        }
        defaults.update({
            "is_active": True,
            "equipment_group": "",
            "menu_label": "",
        })
        partner, _ = Partner.objects.update_or_create(
            name=name,
            defaults=defaults,
        )
        partner.menu_categories.clear()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0023_remove_partner_catalogue_entries"),
        ("core", "0011_customer_portfolio_system"),
    ]

    operations = [
        migrations.RunPython(restore_partners, migrations.RunPython.noop),
    ]
