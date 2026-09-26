import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0004_product_gallery_and_variants"),
        ("orders", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="variant",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="order_items",
                to="catalog.productvariant",
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="variant_model_number",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="variant_name",
            field=models.CharField(blank=True, max_length=180),
        ),
    ]
