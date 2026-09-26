from django.db import migrations


def add_zeiss_partner(apps, schema_editor):
    Partner = apps.get_model("core", "Partner")
    Partner.objects.update_or_create(
        name="ZEISS",
        defaults={
            "country": "Germany",
            "description": (
                "Microscopy systems for scientific research, routine "
                "laboratories, education and industrial inspection."
            ),
            "website": "https://www.zeiss.com/microscopy/en/home.html",
            "display_order": 8,
            "is_active": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0006_zeiss_light_microscope_catalogue"),
        ("core", "0006_merge_duplicate_legacy_projects"),
    ]

    operations = [
        migrations.RunPython(add_zeiss_partner, migrations.RunPython.noop),
    ]
