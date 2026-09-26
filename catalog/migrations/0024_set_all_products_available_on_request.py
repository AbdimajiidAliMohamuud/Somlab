from django.db import migrations


def set_all_products_available_on_request(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    Product.objects.exclude(availability="on_request").update(
        availability="on_request"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0023_remove_partner_catalogue_entries"),
    ]

    operations = [
        migrations.RunPython(
            set_all_products_available_on_request,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
