import django.db.models.deletion
from django.db import migrations, models


def create_mes_full_subcategories(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    ProductSubcategory = apps.get_model("catalog", "ProductSubcategory")

    category = Category.objects.get(slug="medical-electronic-systems")
    definitions = (
        (
            "automated-semen-analysis-solutions",
            "Automated Semen Analysis Solutions",
            "MES clinical automated semen-analysis systems and integration solutions.",
        ),
        (
            "maleman-reference-lab-services",
            "MaleMan Reference Lab Services",
            "MES mail-in reference-laboratory semen-analysis services for providers.",
        ),
        (
            "consumer-semen-analysis-solutions",
            "Consumer Semen Analysis Solutions",
            "MES at-home consumer semen-analysis products.",
        ),
        (
            "semen-analysis-validation-kits",
            "Semen Analysis & Validation Kits",
            "MES testing, advanced-assessment, validation and SQA supplies.",
        ),
        (
            "veterinary-semen-analysis-solutions",
            "Veterinary Semen Analysis Solutions",
            "MES automated semen-analysis systems for bovine, porcine, equine and avian workflows.",
        ),
    )
    for order, (slug, name, description) in enumerate(definitions):
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


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0018_mes_sqa_validation_kits"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductRelatedItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                (
                    "relationship_type",
                    models.CharField(default="included", max_length=40),
                ),
                ("display_order", models.PositiveSmallIntegerField(default=0)),
                (
                    "child_product",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="parent_relations",
                        to="catalog.product",
                    ),
                ),
                (
                    "parent_product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="related_items",
                        to="catalog.product",
                    ),
                ),
            ],
            options={"ordering": ("display_order", "id")},
        ),
        migrations.AddConstraint(
            model_name="productrelateditem",
            constraint=models.UniqueConstraint(
                fields=("parent_product", "name"),
                name="unique_related_item_name_per_product",
            ),
        ),
        migrations.RunPython(
            create_mes_full_subcategories,
            migrations.RunPython.noop,
        ),
    ]
