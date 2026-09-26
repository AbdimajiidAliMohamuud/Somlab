from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0003_customer_portfolio")]

    operations = [
        migrations.AlterField(
            model_name="customer",
            name="display_order",
            field=models.PositiveSmallIntegerField(blank=True, default=0),
        ),
    ]
