from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import migrations, models


SQA_IO_IMAGES = {
    "SQA-iOw Automated Analyzer": "sqa-iow-automated-analyzer.png",
    "SQA-VU Visualization System": "sqa-vu-visualization-system.png",
    "Docking Station for SQA-iOw + VU": "sqa-io-vu-docking-station.png",
    "Desktop PC + Monitor": "sqa-io-desktop-pc-monitor.png",
    "SQA Semen Analysis Test Kit": "sqa-semen-analysis-test-kit.png",
    "SQA QC & Cleaning Kit": "sqa-qc-cleaning-kit.png",
    "QwikCheck Fixed Coverslip Slides": "qwikcheck-fixed-coverslip-slides.png",
    "QwikCheck Proficiency & Training Kit": (
        "qwikcheck-proficiency-training-kit.png"
    ),
}


def add_sqa_io_included_images(apps, schema_editor):
    ProductRelatedItem = apps.get_model("catalog", "ProductRelatedItem")
    image_directory = (
        Path(__file__).resolve().parents[1]
        / "management"
        / "data"
        / "mes_sqa"
        / "images"
    )
    relationships = ProductRelatedItem.objects.using(
        schema_editor.connection.alias
    ).filter(
        parent_product__product_code="SQA-iOw",
        name__in=SQA_IO_IMAGES,
    )
    for relationship in relationships:
        filename = SQA_IO_IMAGES[relationship.name]
        source_path = image_directory / filename
        if not source_path.is_file():
            continue
        stored_name = default_storage.save(
            f"products/related/sqa-iow/{filename}",
            ContentFile(source_path.read_bytes()),
        )
        relationship.image = stored_name
        relationship.save(update_fields=["image"])


def clear_sqa_io_included_images(apps, schema_editor):
    ProductRelatedItem = apps.get_model("catalog", "ProductRelatedItem")
    ProductRelatedItem.objects.using(schema_editor.connection.alias).filter(
        parent_product__product_code="SQA-iOw",
        name__in=SQA_IO_IMAGES,
    ).update(image="")


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0024_set_all_products_available_on_request"),
    ]

    operations = [
        migrations.AddField(
            model_name="productrelateditem",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text=(
                    "Optional image specific to this included or related item."
                ),
                upload_to="products/related/",
            ),
        ),
        migrations.RunPython(
            add_sqa_io_included_images,
            reverse_code=clear_sqa_io_included_images,
        ),
    ]
