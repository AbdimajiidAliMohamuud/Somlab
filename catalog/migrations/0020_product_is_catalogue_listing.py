from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0019_productrelateditem_mes_full_catalogue"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="is_catalogue_listing",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Show this product in catalogue and subcategory product grids."
                ),
            ),
        ),
    ]
