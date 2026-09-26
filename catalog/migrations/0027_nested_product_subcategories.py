from django.db import migrations, models
import django.db.models.deletion


def group_truenat_assays(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    ProductSubcategory = apps.get_model("catalog", "ProductSubcategory")

    try:
        parent = ProductSubcategory.objects.get(
            category__slug="molbio",
            slug="truenat-assays",
        )
    except ProductSubcategory.DoesNotExist:
        return

    groups = (
        ("Respiratory Infections", "respiratory-infections"),
        ("Vector Borne Disease", "vector-borne-disease"),
        ("Hepatitis", "hepatitis"),
        ("Sexually Transmitted Infections", "sexually-transmitted-infections"),
        ("Zoonotic Diseases", "zoonotic-diseases"),
        ("Viral Infections", "viral-infections"),
        ("Bacterial Infections", "bacterial-infections"),
        ("Others", "others"),
    )
    for order, (name, slug) in enumerate(groups):
        child, _ = ProductSubcategory.objects.update_or_create(
            category_id=parent.category_id,
            slug=slug,
            defaults={
                "parent_id": parent.pk,
                "name": name,
                "description": f"Official Molbio Truenat assays listed under {name}.",
                "display_order": order,
                "is_active": True,
            },
        )
        Product.objects.filter(
            subcategory=parent,
            specifications__startswith=f"Assay group: {name}",
        ).update(subcategory=child)


class Migration(migrations.Migration):
    dependencies = [("catalog", "0026_rename_truenat_platform_subcategory")]

    operations = [
        migrations.AddField(
            model_name="productsubcategory",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional parent used for nested catalogue groups.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="children",
                to="catalog.productsubcategory",
            ),
        ),
        migrations.RunPython(group_truenat_assays, migrations.RunPython.noop),
    ]
