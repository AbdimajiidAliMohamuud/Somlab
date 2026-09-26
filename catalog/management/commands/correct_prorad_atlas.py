import hashlib
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from catalog.models import Product, ProductSubcategory
from catalog.prorad_atlas import PRORAD_ATLAS_PRODUCTS


class Command(BaseCommand):
    help = "Keep the three official ProRad Atlas products and import verified images."

    asset_directory = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "molbio"
        / "prorad_atlas"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace-images",
            action="store_true",
            help="Replace existing importer-managed ProRad Atlas media objects.",
        )

    @staticmethod
    def _verified_bytes(asset_path, expected_sha256):
        if not asset_path.is_file():
            raise CommandError(
                f"Missing verified ProRad Atlas asset: {asset_path.name}"
            )
        content = asset_path.read_bytes()
        if hashlib.sha256(content).hexdigest() != expected_sha256:
            raise CommandError(
                f"Checksum mismatch for official ProRad Atlas asset: "
                f"{asset_path.name}"
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
                slug="prorad-atlas",
            )
        except ProductSubcategory.DoesNotExist as exc:
            raise CommandError(
                "The existing ProRad Atlas subcategory was not found."
            ) from exc

        definitions = {item["code"]: item for item in PRORAD_ATLAS_PRODUCTS}
        products = {}
        created_products = 0
        for code, definition in definitions.items():
            specifications = [
                f"{label}: {value}"
                for label, value in definition["specifications"]
            ]
            specifications.append(f"Official source: {definition['source_url']}")
            defaults = {
                "category": subcategory.category,
                "subcategory": subcategory,
                "name": definition["name"],
                "brand": "Molbio Diagnostics",
                "short_description": definition["description"][:240],
                "description": definition["description"],
                "specifications": "\n".join(specifications),
                "price": None,
                "availability": "on_request",
                "is_featured": False,
                "is_active": True,
                "is_catalogue_listing": True,
            }
            product = Product.objects.filter(product_code=code).first()
            if product:
                for field, value in defaults.items():
                    setattr(product, field, value)
                product.save(update_fields=[*defaults, "updated_at"])
            else:
                product = Product.objects.create(
                    slug=f"molbio-{slugify(definition['name'])}",
                    product_code=code,
                    **defaults,
                )
                created_products += 1
            product.variants.all().delete()
            products[code] = product

        extras = Product.objects.filter(subcategory=subcategory).exclude(
            product_code__in=definitions,
        )
        removed = extras.filter(is_active=True).count()
        extras.update(is_active=False)

        stored = reused = 0
        for code, definition in definitions.items():
            product = products[code]
            content = self._verified_bytes(
                self.asset_directory / definition["filename"],
                definition["sha256"],
            )
            storage_name, created = self._store(
                f"products/molbio/prorad-atlas/{definition['filename']}",
                content,
                replace=options["replace_images"],
            )
            stored += int(created)
            reused += int(not created)
            product.image.name = storage_name
            product.source_image.name = storage_name
            product.is_active = True
            product.is_catalogue_listing = True
            product.save(
                update_fields=[
                    "image",
                    "source_image",
                    "is_active",
                    "is_catalogue_listing",
                    "updated_at",
                ]
            )

        hero = PRORAD_ATLAS_PRODUCTS[0]
        hero_content = self._verified_bytes(
            self.asset_directory / hero["filename"],
            hero["sha256"],
        )
        hero_name, created = self._store(
            f"subcategories/molbio/prorad-atlas/{hero['filename']}",
            hero_content,
            replace=options["replace_images"],
        )
        stored += int(created)
        reused += int(not created)
        subcategory.image.name = hero_name
        subcategory.save(update_fields=["image"])

        self.stdout.write(self.style.SUCCESS(
            "ProRad Atlas correction complete: "
            f"3 official products active; {created_products} created; "
            f"{removed} extra product(s) removed; "
            f"{stored} image object(s) stored, {reused} reused."
        ))
