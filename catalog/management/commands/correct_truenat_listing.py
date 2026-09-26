import hashlib
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Product, ProductSubcategory
from catalog.truenat import TRUELAB_PRODUCTS


class Command(BaseCommand):
    help = "Keep only the three approved Truelab products in the Truenat listing."

    asset_directory = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "molbio"
        / "truenat"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace-images",
            action="store_true",
            help="Replace existing importer-managed Truelab image objects.",
        )

    @staticmethod
    def _verified_bytes(asset_path, expected_sha256):
        if not asset_path.is_file():
            raise CommandError(f"Missing verified Truelab asset: {asset_path.name}")
        content = asset_path.read_bytes()
        if hashlib.sha256(content).hexdigest() != expected_sha256:
            raise CommandError(
                f"Checksum mismatch for official Truelab asset: {asset_path.name}"
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
                slug="truenat-platform",
            )
        except ProductSubcategory.DoesNotExist as exc:
            raise CommandError("The existing Truenat subcategory was not found.") from exc

        definitions = {item["code"]: item for item in TRUELAB_PRODUCTS}
        products = Product.objects.filter(product_code__in=definitions)
        found_codes = set(products.values_list("product_code", flat=True))
        missing = sorted(set(definitions) - found_codes)
        if missing:
            raise CommandError(
                "Missing required Truelab products: " + ", ".join(missing)
            )
        if products.exclude(subcategory=subcategory).exists():
            raise CommandError("A required Truelab product is outside the Truenat listing.")

        extras = Product.objects.filter(subcategory=subcategory).exclude(
            product_code__in=definitions,
        )
        removed = extras.filter(is_active=True).count()
        extras.update(is_active=False)

        stored = reused = 0
        for product in products:
            definition = definitions[product.product_code]
            content = self._verified_bytes(
                self.asset_directory / definition["filename"],
                definition["sha256"],
            )
            storage_name, created = self._store(
                f"products/molbio/truenat/{definition['filename']}",
                content,
                replace=options["replace_images"],
            )
            stored += int(created)
            reused += int(not created)
            product.image.name = storage_name
            product.source_image.name = storage_name
            product.is_active = True
            product.save(
                update_fields=[
                    "image",
                    "source_image",
                    "is_active",
                    "updated_at",
                ]
            )

        hero = TRUELAB_PRODUCTS[0]
        hero_content = self._verified_bytes(
            self.asset_directory / hero["filename"],
            hero["sha256"],
        )
        hero_name, created = self._store(
            f"subcategories/molbio/truenat/{hero['filename']}",
            hero_content,
            replace=options["replace_images"],
        )
        stored += int(created)
        reused += int(not created)
        subcategory.name = "Truenat"
        subcategory.image.name = hero_name
        subcategory.save(update_fields=["name", "image"])
        category = subcategory.category
        category.image.name = hero_name
        category.save(update_fields=["image"])

        self.stdout.write(self.style.SUCCESS(
            "Truenat listing correction complete: "
            f"3 approved products active; {removed} extra product(s) removed; "
            f"{stored} image object(s) stored, {reused} reused; "
            "Truelab Duo set as the Truenat and Truenat Real-Time PCR heroes."
        ))
