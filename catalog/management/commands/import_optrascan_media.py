import hashlib
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Product, ProductSubcategory
from catalog.optrascan import OPTRASCAN_PRODUCTS


class Command(BaseCommand):
    help = "Correct the official OptraScan listing and import its verified images."

    asset_directory = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "molbio"
        / "optrascan"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace-images",
            action="store_true",
            help="Replace existing importer-managed OptraScan media objects.",
        )

    @staticmethod
    def _verified_bytes(asset_path, expected_sha256):
        if not asset_path.is_file():
            raise CommandError(f"Missing verified OptraScan asset: {asset_path.name}")
        content = asset_path.read_bytes()
        actual_sha256 = hashlib.sha256(content).hexdigest()
        if actual_sha256 != expected_sha256:
            raise CommandError(
                f"Checksum mismatch for official OptraScan asset: {asset_path.name}"
            )
        return content

    @staticmethod
    def _store(storage_name, content, *, replace=False):
        if replace and default_storage.exists(storage_name):
            default_storage.delete(storage_name)
        if default_storage.exists(storage_name):
            return storage_name, False
        return default_storage.save(storage_name, ContentFile(content)), True

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            subcategory = ProductSubcategory.objects.get(
                category__slug="molbio",
                slug="optrascan",
            )
        except ProductSubcategory.DoesNotExist as exc:
            raise CommandError("The existing OptraScan subcategory was not found.") from exc

        definitions = {item["code"]: item for item in OPTRASCAN_PRODUCTS}
        products = {
            product.product_code: product
            for product in Product.objects.filter(product_code__in=definitions)
        }
        missing = sorted(set(definitions) - set(products))
        if missing:
            raise CommandError(
                "Missing existing OptraScan products: " + ", ".join(missing)
            )

        invalid = Product.objects.filter(subcategory=subcategory).exclude(
            product_code__in=definitions,
        )
        removed = invalid.filter(is_active=True).count()
        invalid.update(is_active=False)

        stored = reused = 0
        for code, definition in definitions.items():
            product = products[code]
            content = self._verified_bytes(
                self.asset_directory / definition["filename"],
                definition["sha256"],
            )
            storage_name, created = self._store(
                f"products/molbio/optrascan/{definition['filename']}",
                content,
                replace=options["replace_images"],
            )
            stored += int(created)
            reused += int(not created)
            product.name = definition["name"]
            product.image.name = storage_name
            product.source_image.name = storage_name
            product.is_active = True
            product.save(
                update_fields=[
                    "name",
                    "image",
                    "source_image",
                    "is_active",
                    "updated_at",
                ]
            )

        hero = OPTRASCAN_PRODUCTS[0]
        hero_content = self._verified_bytes(
            self.asset_directory / hero["filename"],
            hero["sha256"],
        )
        hero_name, created = self._store(
            f"subcategories/molbio/optrascan/{hero['filename']}",
            hero_content,
            replace=options["replace_images"],
        )
        stored += int(created)
        reused += int(not created)
        subcategory.image.name = hero_name
        subcategory.save(update_fields=["image"])

        self.stdout.write(self.style.SUCCESS(
            "OptraScan correction complete: "
            f"5 official products verified, {removed} invalid listing(s) removed; "
            f"{stored} image object(s) stored, {reused} reused."
        ))
