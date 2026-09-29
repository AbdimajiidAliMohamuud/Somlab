from django.db import migrations


def normalize_customer_order(apps, schema_editor):
    Customer = apps.get_model("core", "Customer")
    customers = list(Customer.objects.order_by("display_order", "pk"))
    changed = []
    for index, customer in enumerate(customers):
        if customer.display_order != index:
            customer.display_order = index
            changed.append(customer)
    if changed:
        Customer.objects.bulk_update(changed, ["display_order"])


class Migration(migrations.Migration):
    dependencies = [("core", "0014_aboutpagecontent_contactpagecontent")]

    operations = [migrations.RunPython(normalize_customer_order, migrations.RunPython.noop)]
