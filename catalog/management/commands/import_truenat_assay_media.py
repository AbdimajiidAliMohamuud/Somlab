import hashlib
import json
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from PIL import Image

from catalog.models import Product, ProductSubcategory
from catalog.molbio_source import ASSAY_GROUPS, MOLBIO_PAGES


class Command(BaseCommand):
    help = "Import verified official Truenat assay and assay-group hero images."

    data_file = (
        Path(__file__).resolve().parents[1] / "data" / "molbio" / "products.json"
    )
    asset_directory = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "molbio"
        / "truenat_assays"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace-images",
            action="store_true",
            help="Replace existing importer-managed Truenat assay media objects.",
        )
        parser.add_argument(
            "--replace-assay-images",
            action="store_true",
            help=(
                "Replace only the 36 importer-managed assay images; preserve "
                "the existing assay-group hero objects."
            ),
        )

    @staticmethod
    def _verified_bytes(asset_path):
        if not asset_path.is_file():
            raise CommandError(f"Missing verified Truenat assay asset: {asset_path.name}")
        content = asset_path.read_bytes()
        try:
            with Image.open(BytesIO(content)) as image:
                image.verify()
        except Exception as exc:
            raise CommandError(
                f"Invalid Truenat assay image asset: {asset_path.name}"
            ) from exc
        return content

    @staticmethod
    def _store(storage_name, content, *, replace=False):
        if replace and default_storage.exists(storage_name):
            default_storage.delete(storage_name)
        if default_storage.exists(storage_name):
            return storage_name, False
        return default_storage.save(storage_name, ContentFile(content)), True

    @staticmethod
    def _verify_stored_bytes(storage_name, expected):
        try:
            with default_storage.open(storage_name, "rb") as stored:
                actual = stored.read()
        except Exception as exc:
            raise CommandError(
                f"Unable to read stored Truenat asset: {storage_name}"
            ) from exc
        if actual != expected:
            raise CommandError(
                f"Stored Truenat asset differs from its verified source: "
                f"{storage_name}"
            )

    def _definitions(self):
        source = json.loads(self.data_file.read_text(encoding="utf-8"))
        definitions = [
            item for item in source["products"]
            if item.get("subcategory") == "Truenat Assays"
        ]
        if len(definitions) != 36:
            raise CommandError(
                f"Expected 36 official Truenat assays, found {len(definitions)}."
            )
        if {item.get("group") for item in definitions} != set(ASSAY_GROUPS):
            raise CommandError("The Truenat assay group snapshot is incomplete.")
        for item in definitions:
            if item["source_url"] != MOLBIO_PAGES["assays"]:
                raise CommandError(f"Unexpected source URL for {item['name']}.")
            if item["name"] not in ASSAY_GROUPS[item["group"]]:
                raise CommandError(f"Unexpected group assignment for {item['name']}.")
            if len(item.get("gallery_urls", [])) != 1:
                raise CommandError(
                    f"Expected one official assay-pack image for {item['name']}."
                )
        return definitions

    @transaction.atomic
    def handle(self, *args, **options):
        definitions = self._definitions()
        replace = options["replace_images"]
        replace_assays = replace or options["replace_assay_images"]
        stored = reused = 0

        products = {
            product.name: product
            for product in Product.objects.select_related("subcategory").filter(
                category__slug="molbio",
                product_code__startswith="MOLBIO-ASSAY-",
            )
        }
        expected_names = {item["name"] for item in definitions}
        if set(products) != expected_names:
            missing = sorted(expected_names - set(products))
            extra = sorted(set(products) - expected_names)
            raise CommandError(
                f"Truenat assay records do not match the official snapshot; "
                f"missing={missing}, extra={extra}."
            )

        hero_by_group = {}
        for definition in definitions:
            product = products[definition["name"]]
            expected_subcategory = slugify(definition["group"])
            if (
                not product.subcategory
                or product.subcategory.slug != expected_subcategory
                or not product.subcategory.parent
                or product.subcategory.parent.slug != "truenat-assays"
            ):
                raise CommandError(
                    f"Incorrect nested subcategory for {definition['name']}."
                )

            # Molbio presents the assay-specific primary artwork first, then
            # the matching assay-pack image.  Use the primary artwork for the
            # Included & Related row so every assay retains the distinct image
            # Molbio associates with that exact entry instead of appearing to
            # reuse the common white-box composition across the catalogue.
            product_image_url = definition["image_url"]
            filename = Path(urlparse(product_image_url).path).name
            content = self._verified_bytes(self.asset_directory / filename)
            digest = hashlib.sha256(content).hexdigest()[:12]
            storage_name = (
                "products/molbio/truenat-assays/"
                f"{expected_subcategory}/{digest}-{filename}"
            )
            stored_name, created = self._store(
                storage_name,
                content,
                replace=replace_assays,
            )
            self._verify_stored_bytes(stored_name, content)
            stored += int(created)
            reused += int(not created)
            product.image.name = stored_name
            product.source_image.name = stored_name
            product.save(update_fields=["image", "source_image", "updated_at"])
            if definition["group"] not in hero_by_group:
                hero_filename = Path(
                    urlparse(definition["image_url"]).path
                ).name
                hero_content = self._verified_bytes(
                    self.asset_directory / hero_filename
                )
                hero_digest = hashlib.sha256(hero_content).hexdigest()[:12]
                hero_by_group[definition["group"]] = (
                    hero_filename,
                    hero_content,
                    hero_digest,
                )

        for group_name, (filename, content, digest) in hero_by_group.items():
            group = ProductSubcategory.objects.get(
                category__slug="molbio",
                parent__slug="truenat-assays",
                slug=slugify(group_name),
            )
            hero_name, created = self._store(
                "subcategories/molbio/truenat-assays/"
                f"{group.slug}/{digest}-{filename}",
                content,
                replace=replace,
            )
            self._verify_stored_bytes(hero_name, content)
            stored += int(created)
            reused += int(not created)
            group.image.name = hero_name
            group.save(update_fields=["image"])

        self.stdout.write(self.style.SUCCESS(
            "Truenat assay media complete: 36 official assay images and "
            f"8 group hero images verified; {stored} object(s) stored, "
            f"{reused} reused."
        ))
