from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.ibreastexam import (
    IBREASTEXAM_FEATURES,
    IBREASTEXAM_HERO,
    IBREASTEXAM_PRODUCT_CODE,
)
from catalog.models import Product, ProductMedia


class Command(BaseCommand):
    help = "Import the verified official iBreastExam product and section images."

    asset_directory = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "molbio"
        / "ibreastexam"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace-images",
            action="store_true",
            help="Replace existing importer-managed iBreastExam media objects.",
        )

    def _store(self, storage_name, asset_path, *, replace=False):
        if not asset_path.is_file():
            raise CommandError(f"Missing verified iBreastExam asset: {asset_path.name}")
        if replace and default_storage.exists(storage_name):
            default_storage.delete(storage_name)
        if default_storage.exists(storage_name):
            return storage_name, False
        stored_name = default_storage.save(
            storage_name,
            ContentFile(asset_path.read_bytes()),
        )
        return stored_name, True

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            product = Product.objects.select_related("subcategory").get(
                product_code=IBREASTEXAM_PRODUCT_CODE,
            )
        except Product.DoesNotExist as exc:
            raise CommandError("The existing iBreastExam product was not found.") from exc

        if not product.subcategory:
            raise CommandError("The existing iBreastExam subcategory was not found.")

        replace = options["replace_images"]
        stored = reused = 0
        hero_asset = self.asset_directory / IBREASTEXAM_HERO["filename"]

        product_name, created = self._store(
            "products/molbio/ibreastexam/interface-new.jpg",
            hero_asset,
            replace=replace,
        )
        stored += int(created)
        reused += int(not created)
        product.image.name = product_name
        product.source_image.name = product_name
        product.save(update_fields=["image", "source_image", "updated_at"])

        subcategory_name, created = self._store(
            "subcategories/molbio/ibreastexam/interface-new.jpg",
            hero_asset,
            replace=replace,
        )
        stored += int(created)
        reused += int(not created)
        product.subcategory.image.name = subcategory_name
        product.subcategory.save(update_fields=["image"])

        managed_names = []
        for feature in IBREASTEXAM_FEATURES:
            storage_name = (
                "products/gallery/molbio/ibreastexam/"
                f"{feature['display_order']}-{feature['filename']}"
            )
            managed_names.append(storage_name)
            stored_name, created = self._store(
                storage_name,
                self.asset_directory / feature["filename"],
                replace=replace,
            )
            stored += int(created)
            reused += int(not created)
            media, _ = ProductMedia.objects.get_or_create(
                product=product,
                file=stored_name,
                defaults={
                    "media_type": "image",
                    "display_order": feature["display_order"],
                },
            )
            update_fields = []
            if media.media_type != "image":
                media.media_type = "image"
                update_fields.append("media_type")
            if media.display_order != feature["display_order"]:
                media.display_order = feature["display_order"]
                update_fields.append("display_order")
            if update_fields:
                media.save(update_fields=update_fields)

        ProductMedia.objects.filter(
            product=product,
            file__startswith="products/gallery/molbio/ibreastexam/",
        ).exclude(file__in=managed_names).delete()

        self.stdout.write(self.style.SUCCESS(
            "iBreastExam media complete: "
            f"{stored} object(s) stored, {reused} reused; "
            "1 product image, 1 subcategory image and 4 feature images verified."
        ))

