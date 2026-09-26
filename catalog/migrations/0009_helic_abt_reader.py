from django.db import migrations


def add_helic_abt_reader(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    Partner = apps.get_model("core", "Partner")

    category, _ = Category.objects.update_or_create(
        slug="ama-helic-ubt-reader",
        defaults={
            "name": "AMA Helic UBT Reader",
            "description": (
                "Non-invasive Helicobacter pylori breath-testing "
                "equipment from AMA-Med."
            ),
            "icon": "analyser",
            "display_order": 8,
            "is_active": True,
        },
    )
    partner, _ = Partner.objects.update_or_create(
        name="AMA Helic UBT Reader",
        defaults={
            "country": "Finland",
            "website": "https://www.helicabt.com/",
            "equipment_group": "laboratory",
            "menu_label": "AMA Helic UBT Reader",
            "menu_order": 4,
            "is_active": True,
        },
    )
    partner.menu_categories.set([category])
    Product.objects.update_or_create(
        product_code="AMA-HELIC-ABT-READER",
        defaults={
            "category": category,
            "subcategory": None,
            "name": "HELIC® ABT Reader",
            "slug": "helic-abt-reader",
            "brand": "AMA Helic UBT Reader",
            "short_description": (
                "An automatic reader for non-invasive Helicobacter pylori "
                "ammonia breath testing."
            ),
            "description": (
                "The HELIC® ABT Reader automatically samples exhaled air "
                "and reads the colour of an indicator tube for qualitative "
                "detection of Helicobacter pylori urease activity. Its PC "
                "software guides the examination, displays results, "
                "maintains a database and supports report printing."
            ),
            "specifications": (
                "Test method: non-invasive ammonia breath test\n"
                "Operation: automatic air sampling and indicator-tube colour reading\n"
                "Result time: 11 minutes\n"
                "Sensitivity: 95%\n"
                "Specificity: 92%\n"
                "Result display: graphical result on a connected computer\n"
                "Software: guided examination, database and report printing\n"
                "Batch configuration: QR-coded indicator-tube parameters\n"
                "Maintenance: no periodic maintenance required\n"
                "Computer: not included"
            ),
            "price": None,
            "availability": "on_request",
            "is_featured": False,
            "is_active": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0008_eschweiler_catalogue_category"),
        ("core", "0010_alter_partner_menu_order"),
    ]

    operations = [
        migrations.RunPython(add_helic_abt_reader, migrations.RunPython.noop),
    ]
