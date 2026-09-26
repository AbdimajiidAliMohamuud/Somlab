import json
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from catalog.images import normalize_product_image
from catalog.models import Category, Product, ProductSubcategory
from core.models import Partner


class Command(BaseCommand):
    help = "Reconcile the current official ZEISS Light Microscopes catalogue."

    image_directory = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "zeiss_light_microscopes"
    )

    expected_product_codes = frozenset(
        json.loads(
            (image_directory / "image_sources.json").read_text(encoding="utf-8")
        )
    )
    category_representative = "ZEISS-LM-WF-008"
    subcategory_representatives = {
        "widefield-microscopes": "ZEISS-LM-WF-003",
        "stereo-and-zoom-microscopes": "ZEISS-LM-SZ-007",
        "digital-microscopes": "ZEISS-LM-DM-002",
        "super-resolution-microscopes": "ZEISS-LM-SR-001",
        "light-sheet-microscopes": "ZEISS-LM-LS-002",
        "confocal-laser-scanning-microscopes": "ZEISS-LM-CF-003",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace-images",
            action="store_true",
            help=(
                "Replace an existing ZEISS image with the verified bundled "
                "official image. By default, existing admin uploads are preserved."
            ),
        )
        parser.add_argument(
            "--subcategory-images-only",
            action="store_true",
            help="Import only the six verified ZEISS subcategory images.",
        )

    def import_images(self, *, replace_images=False):
        sources_path = self.image_directory / "image_sources.json"
        image_sources = json.loads(sources_path.read_text(encoding="utf-8"))
        imported = preserved = missing_products = missing_assets = 0

        for product_code in image_sources:
            try:
                product = Product.objects.get(product_code=product_code)
            except Product.DoesNotExist:
                missing_products += 1
                self.stderr.write(f"Missing product: {product_code}")
                continue

            asset_path = self.image_directory / f"{product_code.lower()}.jpg"
            if not asset_path.is_file():
                missing_assets += 1
                self.stderr.write(f"Missing image asset: {asset_path.name}")
                continue

            if product.image and not replace_images:
                preserved += 1
                continue

            storage_name = f"products/zeiss/fit-v2/{asset_path.stem}.webp"
            if default_storage.exists(storage_name):
                product.image.name = storage_name
                product.save(update_fields=["image", "updated_at"])
            else:
                product.image.save(
                    f"zeiss/fit-v2/{asset_path.stem}.webp",
                    normalize_product_image(asset_path.open("rb"), filename=asset_path.name),
                    save=True,
                )
            imported += 1

        return imported, preserved, missing_products, missing_assets

    def import_category_image(self, category, *, replace_images=False):
        product_code = self.category_representative
        asset_path = self.image_directory / f"{product_code.lower()}.jpg"
        if not asset_path.is_file():
            self.stderr.write(f"Missing category image asset: {asset_path.name}")
            return 0, 0, 1
        if category.image and not replace_images:
            return 0, 1, 0

        storage_name = (
            f"categories/zeiss/light-microscopes-{product_code.lower()}.jpg"
        )
        if default_storage.exists(storage_name):
            category.image.name = storage_name
            category.save(update_fields=["image"])
        else:
            category.image.save(
                f"zeiss/light-microscopes-{product_code.lower()}.jpg",
                ContentFile(asset_path.read_bytes()),
                save=True,
            )
        return 1, 0, 0

    def import_subcategory_images(self, category, *, replace_images=False):
        imported = preserved = missing_assets = 0
        for subcategory_slug, product_code in (
            self.subcategory_representatives.items()
        ):
            subcategory = ProductSubcategory.objects.get(
                category=category,
                slug=subcategory_slug,
            )
            asset_path = (
                self.image_directory / f"{product_code.lower()}-cutout.png"
            )
            if not asset_path.is_file():
                missing_assets += 1
                self.stderr.write(
                    f"Missing subcategory image asset: {asset_path.name}"
                )
                continue
            if subcategory.image and not replace_images:
                preserved += 1
                continue

            storage_name = (
                f"subcategories/zeiss/{subcategory_slug}-{product_code.lower()}-cutout.png"
            )
            if default_storage.exists(storage_name):
                subcategory.image.name = storage_name
                subcategory.save(update_fields=["image"])
            else:
                subcategory.image.save(
                    f"zeiss/{subcategory_slug}-{product_code.lower()}-cutout.png",
                    ContentFile(asset_path.read_bytes()),
                    save=True,
                )
            imported += 1

        return imported, preserved, missing_assets

    def audit_catalogue(self, category):
        zeiss_products = Product.objects.filter(brand__iexact="ZEISS")
        actual_codes = set(zeiss_products.values_list("product_code", flat=True))
        missing_codes = sorted(self.expected_product_codes - actual_codes)
        unexpected_codes = sorted(actual_codes - self.expected_product_codes)
        misplaced_codes = sorted(
            zeiss_products.exclude(category=category).values_list(
                "product_code", flat=True,
            )
        )
        ungrouped_codes = sorted(
            zeiss_products.filter(
                category=category,
                subcategory__isnull=True,
            ).values_list("product_code", flat=True)
        )
        return missing_codes, unexpected_codes, misplaced_codes, ungrouped_codes

    def handle(self, *args, **options):
        category = Category.objects.get(slug="light-microscopes")
        if options["subcategory_images_only"]:
            category_imported, category_preserved, category_missing = (
                self.import_category_image(
                    category,
                    replace_images=options["replace_images"],
                )
            )
            imported, preserved, missing = self.import_subcategory_images(
                category,
                replace_images=options["replace_images"],
            )
            self.stdout.write(self.style.SUCCESS(
                "ZEISS category image: "
                f"{category_imported} imported, {category_preserved} preserved, "
                f"{category_missing} missing; subcategory images: "
                f"{imported} imported, {preserved} preserved, {missing} missing."
            ))
            return

        category.name = "ZEISS Light Microscopes"
        category.menu_label = "ZEISS Light Microscopes"
        category.is_active = True
        category.save(update_fields=["name", "menu_label", "is_active"])

        stereo = ProductSubcategory.objects.get(
            category=category,
            slug="stereo-and-zoom-microscopes",
        )
        stereo.name = "Stereo & Zoom Microscopes"
        stereo.save(update_fields=["name"])
        widefield = ProductSubcategory.objects.get(
            category=category,
            slug="widefield-microscopes",
        )

        product, created = Product.objects.update_or_create(
            product_code="ZEISS-LM-WF-019",
            defaults={
                "category": category,
                "subcategory": widefield,
                "name": "ZEISS Axiovert for Materials",
                "slug": "zeiss-axiovert-materials",
                "brand": "ZEISS",
                "short_description": (
                    "Inverted microscopes for materials laboratories and "
                    "smart digital documentation."
                ),
                "description": (
                    "ZEISS Axiovert supports high-quality imaging of large "
                    "and heavy materials samples using reflected or "
                    "transmitted light. Axiovert 5 supports standalone smart "
                    "documentation, while Axiovert 7 adds motorized workflow "
                    "automation."
                ),
                "specifications": (
                    "Format: Inverted widefield microscope\n"
                    "Application: Materials laboratory and materialography\n"
                    "Contrast methods: Reflected and transmitted light\n"
                    "Models: Axiovert 5 and Axiovert 7\n"
                    "Documentation: Standalone operation available with Axiovert 5\n"
                    "Automation: Motorized Z-focus and XY stage available with Axiovert 7"
                ),
                "price": None,
                "availability": "on_request",
                "is_featured": False,
                "is_active": True,
            },
        )

        partner = Partner.objects.get(name="ZEISS")
        partner.menu_label = "ZEISS Microscopy"
        partner.equipment_group = "medical"
        partner.is_active = True
        partner.save(update_fields=[
            "menu_label", "equipment_group", "is_active",
        ])
        partner.menu_categories.set([category])

        missing_codes, unexpected_codes, misplaced_codes, ungrouped_codes = (
            self.audit_catalogue(category)
        )
        if missing_codes:
            self.stderr.write(f"Missing ZEISS codes: {', '.join(missing_codes)}")
        if unexpected_codes:
            self.stderr.write(
                f"Unexpected ZEISS codes (not removed): {', '.join(unexpected_codes)}"
            )
        if misplaced_codes:
            self.stderr.write(
                f"ZEISS products outside Light Microscopes: "
                f"{', '.join(misplaced_codes)}"
            )
        if ungrouped_codes:
            self.stderr.write(
                f"ZEISS products without a Light Microscope group: "
                f"{', '.join(ungrouped_codes)}"
            )

        imported, preserved, missing_products, missing_assets = self.import_images(
            replace_images=options["replace_images"],
        )
        (
            category_image_imported,
            category_image_preserved,
            category_image_missing,
        ) = self.import_category_image(
            category,
            replace_images=options["replace_images"],
        )
        (
            subcategory_images_imported,
            subcategory_images_preserved,
            subcategory_images_missing,
        ) = self.import_subcategory_images(
            category,
            replace_images=options["replace_images"],
        )

        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Updated'} {product.name}; "
            "reconciled ZEISS medical navigation; "
            f"imported {imported} image(s), preserved {preserved}, "
            f"missing products {missing_products}, missing assets {missing_assets}; "
            f"category image: {category_image_imported} imported, "
            f"{category_image_preserved} preserved, "
            f"{category_image_missing} missing; "
            f"subcategory images: {subcategory_images_imported} imported, "
            f"{subcategory_images_preserved} preserved, "
            f"{subcategory_images_missing} missing; "
            f"catalogue audit: {len(missing_codes)} missing, "
            f"{len(unexpected_codes)} unexpected, {len(misplaced_codes)} misplaced, "
            f"{len(ungrouped_codes)} ungrouped."
        ))
