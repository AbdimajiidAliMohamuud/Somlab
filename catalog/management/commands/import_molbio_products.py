import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from catalog.models import (
    Category,
    Product,
    ProductMedia,
    ProductSubcategory,
    ProductVariant,
)
from catalog.molbio_source import (
    ASSAY_GROUPS,
    MOLBIO_BASE_URL,
    build_molbio_catalogue,
    fetch_molbio_pages,
)
from core.models import Partner


BRAND = "Molbio Diagnostics"
EXPECTED_PRODUCT_COUNT = 48
DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "molbio" / "products.json"
GROUPS = (
    ("Truenat", "truenat-platform", "Portable sample preparation and real-time micro-PCR instruments."),
    ("Truenat Assays", "truenat-assays", "Chip-based real-time PCR assays across the official Truenat diagnostic portfolio."),
    ("iBreastExam", "ibreastexam", "Point-of-care, non-invasive breast health screening."),
    ("ProRad Atlas", "prorad-atlas", "Ultra-portable point-of-care digital X-ray imaging."),
    ("OptraScan", "optrascan", "Whole-slide scanners and digital pathology workflows."),
)
ASSAY_GROUP_DESCRIPTIONS = {
    name: f"Official Molbio Truenat assays listed under {name}."
    for name in ASSAY_GROUPS
}


class Command(BaseCommand):
    help = "Import the verified official Molbio Diagnostics catalogue."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="Deprecated compatibility flag; Molbio images are never imported.",
        )
        parser.add_argument(
            "--clear-images",
            action="store_true",
            help=(
                "Clear all Molbio main/source images and imported image gallery "
                "records without contacting remote storage."
            ),
        )
        parser.add_argument(
            "--refresh-source",
            action="store_true",
            help="Refresh the bundled source snapshot from Molbio before importing.",
        )

    def handle(self, *args, **options):
        catalogue = self._catalogue(options["refresh_source"])
        if len(catalogue) != EXPECTED_PRODUCT_COUNT:
            raise CommandError(
                f"Expected {EXPECTED_PRODUCT_COUNT} official Molbio products, "
                f"received {len(catalogue)}; import stopped."
            )

        cleared_main = cleared_gallery = 0
        if options["clear_images"]:
            cleared_main, cleared_gallery = self._clear_images()

        with transaction.atomic():
            category, _ = Category.objects.update_or_create(
                slug="molbio",
                defaults={
                    "name": "Molbio",
                    "menu_label": "Molbio",
                    "description": (
                        "Molbio Diagnostics point-of-care molecular diagnostics, "
                        "screening, portable radiology and digital pathology solutions."
                    ),
                    "icon": "test-tube",
                    "display_order": 11,
                    "is_active": True,
                },
            )
            subcategories = {}
            for order, (name, slug, description) in enumerate(GROUPS):
                subcategories[name], _ = ProductSubcategory.objects.update_or_create(
                    category=category,
                    slug=slug,
                    defaults={
                        "name": name,
                        "parent": None,
                        "description": description,
                        "display_order": order,
                        "is_active": True,
                    },
                )

            assay_parent = subcategories["Truenat Assays"]
            assay_subcategories = {}
            for order, group_name in enumerate(ASSAY_GROUPS):
                group_slug = slugify(group_name)
                assay_subcategories[group_name], _ = (
                    ProductSubcategory.objects.update_or_create(
                        category=category,
                        slug=group_slug,
                        defaults={
                            "parent": assay_parent,
                            "name": group_name,
                            "description": ASSAY_GROUP_DESCRIPTIONS[group_name],
                            "display_order": order,
                            "is_active": True,
                        },
                    )
                )

            partner, _ = Partner.objects.update_or_create(
                name=BRAND,
                defaults={
                    "country": "India",
                    "website": MOLBIO_BASE_URL,
                    "description": (
                        "Diagnostics manufacturer developing portable molecular testing, "
                        "screening and imaging solutions for decentralized healthcare."
                    ),
                    "equipment_group": "laboratory",
                    "menu_label": "Molbio",
                    "menu_order": 3,
                    "is_active": True,
                },
            )
            partner.menu_categories.set([category])

            created = updated = 0
            imported_codes = set()
            for definition in catalogue:
                code = self._product_code(definition)
                imported_codes.add(code)
                slug = f"molbio-{slugify(definition['name'])}"
                defaults = self._product_defaults(
                    definition, category, subcategories, assay_subcategories
                )
                defaults["product_code"] = code
                product = None
                if code.startswith(("MOLBIO-OPTRASCAN-", "MOLBIO-PRORAD-")):
                    product = Product.objects.filter(product_code=code).first()
                if product:
                    for field, value in defaults.items():
                        setattr(product, field, value)
                    product.save(update_fields=[*defaults, "updated_at"])
                    was_created = False
                else:
                    product, was_created = Product.objects.update_or_create(
                        slug=slug,
                        defaults=defaults,
                    )
                created += int(was_created)
                updated += int(not was_created)
                self._replace_variants(product, definition.get("variants", []))

            # Only retire stale items previously controlled by this importer.
            Product.objects.filter(
                category=category,
                brand__iexact=BRAND,
            ).exclude(product_code__in=imported_codes).update(is_active=False)

        self.stdout.write(self.style.SUCCESS(
            f"Molbio catalogue complete: {created} created, {updated} updated, "
            f"{len(catalogue)} verified products; no images imported. "
            f"Cleared {cleared_main} product image records and "
            f"{cleared_gallery} gallery image records."
        ))

    @staticmethod
    def _clear_images():
        """Clear Molbio image references without reading/deleting R2 objects.

        The files were importer-managed and may be unavailable remotely. The
        catalogue must remain editable even when R2 is offline, so cleanup is a
        database-only operation. Videos, if admins add them, are preserved.
        """
        products = Product.objects.filter(brand__iexact=BRAND)
        cleared_main = products.filter(image__gt="").count()
        Product.objects.filter(pk__in=products).update(image="", source_image="")
        gallery = ProductMedia.objects.filter(
            product__in=products,
            media_type="image",
        )
        cleared_gallery = gallery.count()
        gallery.delete()
        return cleared_main, cleared_gallery

    def _catalogue(self, refresh):
        if refresh:
            catalogue = build_molbio_catalogue(fetch_molbio_pages())
            DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            DATA_FILE.write_text(
                json.dumps(
                    {"source": MOLBIO_BASE_URL, "products": catalogue},
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            return catalogue
        if not DATA_FILE.exists():
            raise CommandError(
                "Molbio source snapshot is missing; rerun with --refresh-source."
            )
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))["products"]

    @staticmethod
    def _product_code(definition):
        if definition.get("code"):
            return definition["code"]
        if definition.get("subcategory") == "Truenat Assays":
            # Catalogue numbers identify pack variants and Molbio currently
            # publishes one duplicate number across two assays.  Keep those
            # official numbers on ProductVariant and use an unambiguous stable
            # internal product identifier for the parent assay record.
            return f"MOLBIO-ASSAY-{slugify(definition['name']).upper()}"
        first_sku = next(
            (variant.get("sku") for variant in definition.get("variants", []) if variant.get("sku")),
            "",
        )
        return first_sku or f"MOLBIO-{slugify(definition['name']).upper()}"

    @staticmethod
    def _product_defaults(
        definition, category, subcategories, assay_subcategories
    ):
        specifications = []
        if definition.get("group"):
            specifications.append(f"Assay group: {definition['group']}")
        specifications.extend(
            f"{key}: {value}" for key, value in definition.get("specifications", [])
        )
        if definition.get("kit_contents"):
            specifications.append("Kit contents:")
            specifications.extend(
                f"  {item}" for item in definition["kit_contents"]
            )
        if definition.get("source_url"):
            specifications.append(f"Official source: {definition['source_url']}")

        description = definition["description"].strip()
        assigned_subcategory = (
            assay_subcategories[definition["group"]]
            if definition.get("group")
            else subcategories[definition["subcategory"]]
        )
        return {
            "category": category,
            "subcategory": assigned_subcategory,
            "name": definition["name"],
            "brand": BRAND,
            "short_description": description[:240],
            "description": description,
            "specifications": "\n".join(specifications),
            "price": None,
            "availability": "on_request",
            "is_featured": False,
            "is_active": True,
        }

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
