import json
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Category, Product, ProductSubcategory, ProductVariant
from core.models import Partner


BRAND = "SD Biosensor"
CATEGORY_SLUG = "sd-biosensor"
SUBCATEGORY_SLUG = "standard-q"
EXPECTED_CODES = {
    "09MAL30D",
    "09HCV10D",
    "09HBS10D",
    "09HIV30D",
    "09SYP10D",
}
DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "sd_biosensor"
DATA_FILE = DATA_DIRECTORY / "products.json"


class Command(BaseCommand):
    help = "Import only the five approved SD BIOSENSOR STANDARD Q rapid tests."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="Import catalogue records without storing the bundled official images.",
        )
        parser.add_argument(
            "--replace-images",
            action="store_true",
            help="Replace images previously assigned to these five products.",
        )

    def handle(self, *args, **options):
        catalogue = self._catalogue()
        received_codes = {definition["code"] for definition in catalogue}
        if len(catalogue) != 5 or received_codes != EXPECTED_CODES:
            raise CommandError(
                "The SD BIOSENSOR import is locked to the five approved "
                "STANDARD Q catalogue numbers."
            )

        with transaction.atomic():
            category, _ = Category.objects.update_or_create(
                slug=CATEGORY_SLUG,
                defaults={
                    "name": "SD Biosensor Rapid Test",
                    "menu_label": "SD Biosensor Rapid Test",
                    "description": (
                        "Selected STANDARD Q rapid diagnostic tests from "
                        "SD BIOSENSOR for malaria, hepatitis and blood-borne infections."
                    ),
                    "icon": "test-tube",
                    "display_order": 12,
                    "is_active": True,
                },
            )
            standard_q, _ = ProductSubcategory.objects.update_or_create(
                category=category,
                slug=SUBCATEGORY_SLUG,
                defaults={
                    "name": "STANDARD Q",
                    "description": (
                        "Rapid immunochromatographic tests selected from the official "
                        "SD BIOSENSOR STANDARD Q range."
                    ),
                    "display_order": 0,
                    "is_active": True,
                },
            )
            partner, _ = Partner.objects.update_or_create(
                name=BRAND,
                defaults={
                    "country": "South Korea",
                    "website": "https://www.sdbiosensor.com",
                    "description": (
                        "Global in vitro diagnostics manufacturer supplying rapid, "
                        "fluorescence, molecular and immunoassay systems."
                    ),
                    "equipment_group": "laboratory",
                    "menu_label": "SD Biosensor",
                    "menu_order": 5,
                    "is_active": True,
                },
            )
            partner.menu_categories.set([category])

            created = updated = images_imported = 0
            for definition in catalogue:
                defaults = {
                    "category": category,
                    "subcategory": standard_q,
                    "name": definition["name"],
                    "slug": definition["slug"],
                    "brand": BRAND,
                    "short_description": definition["short_description"],
                    "description": definition["description"],
                    "specifications": self._specifications(definition),
                    "price": None,
                    "availability": "on_request",
                    "is_featured": False,
                    "is_active": True,
                }
                product, was_created = Product.objects.update_or_create(
                    product_code=definition["code"],
                    defaults=defaults,
                )
                created += int(was_created)
                updated += int(not was_created)
                self._replace_variants(product, definition.get("variants", []))
                if not options["skip_images"]:
                    images_imported += int(self._attach_image(
                        product,
                        definition,
                        replace=options["replace_images"],
                    ))

            # This importer controls only this category and never touches
            # unrelated SD BIOSENSOR or Somlab catalogue records.
            Product.objects.filter(
                category=category,
                brand__iexact=BRAND,
            ).exclude(product_code__in=EXPECTED_CODES).update(is_active=False)

        self.stdout.write(self.style.SUCCESS(
            f"SD BIOSENSOR STANDARD Q catalogue complete: {created} created, "
            f"{updated} updated, {images_imported} images stored; "
            "5 approved products verified."
        ))

    @staticmethod
    def _catalogue():
        if not DATA_FILE.exists():
            raise CommandError(f"Missing bundled catalogue data: {DATA_FILE}")
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))["products"]

    @staticmethod
    def _specifications(definition):
        lines = [
            f"{label}: {value}"
            for label, value in definition.get("specifications", [])
        ]
        lines.append(f"Official source: {definition['source_url']}")
        return "\n".join(lines)

    @staticmethod
    def _replace_variants(product, variants):
        product.variants.all().delete()
        ProductVariant.objects.bulk_create([
            ProductVariant(
                product=product,
                name=variant.get("name", ""),
                model_number=variant.get("sku", ""),
                display_order=index,
            )
            for index, variant in enumerate(variants)
            if variant.get("name") or variant.get("sku")
        ])

    @staticmethod
    def _attach_image(product, definition, *, replace):
        if product.image and not replace:
            return False
        image_path = DATA_DIRECTORY / definition["image_filename"]
        if not image_path.is_file():
            raise CommandError(f"Missing bundled official image: {image_path}")
        product.image = ContentFile(
            image_path.read_bytes(),
            name=definition["image_filename"],
        )
        product.save()
        return True
