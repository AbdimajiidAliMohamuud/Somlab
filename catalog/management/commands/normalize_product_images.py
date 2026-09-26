from pathlib import Path

from django.core.management.base import BaseCommand

from catalog.images import normalize_product_image
from catalog.models import Product, ProductMedia


class Command(BaseCommand):
    help = "Normalize existing product and gallery images without changing product data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Inspect eligible images without writing replacements.",
        )
        parser.add_argument(
            "--brand",
            help="Limit main product images to one brand (case-insensitive).",
        )
        parser.add_argument(
            "--reprocess",
            action="store_true",
            help="Regenerate normalized derivatives from retained original images.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        updated = skipped = failed = 0
        products = Product.objects.exclude(image="")
        if options.get("brand"):
            products = products.filter(brand__iexact=options["brand"])
        records = [
            (product, "image", "source_image")
            for product in products.iterator()
        ]
        gallery = ProductMedia.objects.filter(media_type="image").exclude(file="")
        if options.get("brand"):
            gallery = gallery.filter(product__brand__iexact=options["brand"])
        records += [
            (media, "file", "source_file")
            for media in gallery.iterator()
        ]

        for record, field_name, source_field_name in records:
            field = getattr(record, field_name)
            if "/normalized/" in field.name and not options["reprocess"]:
                skipped += 1
                continue
            source_field = getattr(record, source_field_name, None)
            source_name = source_field.name if source_field and source_field.name else ""
            if not source_name and "/normalized/" in field.name:
                candidate = field.name.replace("/normalized/", "/", 1)
                try:
                    if field.storage.exists(candidate):
                        source_name = candidate
                except Exception:
                    pass
            source_name = source_name or field.name
            try:
                with field.storage.open(source_name, "rb") as source:
                    normalized = normalize_product_image(source, filename=source_name)
            except Exception as error:
                # Legacy rows can reference an original that was removed before
                # source retention existed. The current derivative remains a
                # safe reprocessing input and must not make the batch fail.
                fallback = self._bundled_fallback(source_name)
                try:
                    current_available = source_name != field.name and field.storage.exists(field.name)
                except Exception:
                    current_available = False
                if current_available:
                    with field.storage.open(field.name, "rb") as source:
                        normalized = normalize_product_image(source, filename=field.name)
                elif fallback:
                    with fallback.open("rb") as source:
                        normalized = normalize_product_image(source, filename=source_name)
                else:
                    failed += 1
                    self.stderr.write(f"Skipped {source_name}: {error}")
                    continue

            if dry_run:
                updated += 1
                continue

            destination = (
                f"products/normalized/{Path(field.name).stem}.webp"
                if field_name == "image"
                else f"products/gallery/normalized/{Path(field.name).stem}.webp"
            )
            saved_name = field.storage.save(destination, normalized)
            updates = {field_name: saved_name}
            if source_name != saved_name and not (source_field and source_field.name):
                updates[source_field_name] = source_name
            type(record).objects.filter(pk=record.pk).update(**updates)
            updated += 1

        action = "eligible" if dry_run else "normalized"
        self.stdout.write(
            self.style.SUCCESS(
                f"Product media {action}: {updated}; already normalized: {skipped}; unavailable: {failed}."
            )
        )

    @staticmethod
    def _bundled_fallback(storage_name):
        filename = Path(storage_name).name.split("_", 1)[0]
        data_root = Path(__file__).resolve().parents[1] / "data"
        candidates = (
            data_root / "eschweiler" / filename,
            data_root / "vatech_dental" / filename,
            data_root / "zeiss_light_microscopes" / filename,
        )
        return next((candidate for candidate in candidates if candidate.is_file()), None)
