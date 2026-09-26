import json
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image, UnidentifiedImageError

from catalog.models import (
    Category,
    Product,
    ProductRelatedItem,
    ProductSubcategory,
)
from core.models import Partner


BRAND = "Medical Electronic Systems"
CATEGORY_SLUG = "medical-electronic-systems"
EXPECTED_SUBCATEGORIES = {
    "automated-semen-analysis-solutions",
    "consumer-semen-analysis-solutions",
    "maleman-reference-lab-services",
    "semen-analysis-validation-kits",
    "veterinary-semen-analysis-solutions",
}
EXPECTED_LISTING_CODES = {
    "SQA-Vision",
    "SQA-iOw",
    "SQA-V Gold",
    "QwikCheck Gold",
    "MaleMan Reference Lab Services",
    "YO Home Sperm Test Kit",
    "MES-QWIKCHECK-TEST-KITS",
    "MES-ADVANCED-TESTING-KITS",
    "MES-QWIKCHECK-VALIDATION-KITS",
    "MES-QWIKCHECK-SQA-SUPPLIES",
    "SQA-Vb",
    "SQA-Vp",
    "SQA-Ve",
    "SQA-Vt",
}
DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "mes_sqa"
DATA_FILE = DATA_DIRECTORY / "products.json"


class Command(BaseCommand):
    help = "Import the approved MES catalogue hierarchy and official item images."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="Import catalogue records without storing bundled official images.",
        )
        parser.add_argument(
            "--replace-images",
            action="store_true",
            help="Replace MES images already assigned by this catalogue import.",
        )
        parser.add_argument(
            "--relationship-parent",
            action="append",
            default=[],
            metavar="PRODUCT_CODE",
            help=(
                "Update Included & Related rows only for this existing MES "
                "parent product. May be supplied more than once."
            ),
        )

    def handle(self, *args, **options):
        catalogue = self._catalogue()
        products = catalogue.get("products", [])
        product_codes = [definition["code"] for definition in products]
        received_subcategories = {
            definition["slug"] for definition in catalogue.get("subcategories", [])
        }
        listing_codes = set(catalogue.get("catalogue_product_codes", []))
        expected_count = catalogue.get("expected_product_count")
        if (
            len(products) != expected_count
            or len(set(product_codes)) != expected_count
            or received_subcategories != EXPECTED_SUBCATEGORIES
            or listing_codes != EXPECTED_LISTING_CODES
        ):
            raise CommandError(
                "The MES import data must contain the five official product "
                "families and the declared number of unique catalogue items."
            )
        for relationship in catalogue.get("relationships", []):
            if relationship["parent_code"] not in product_codes:
                raise CommandError(
                    "Every MES relationship parent must be a catalogue item."
                )
            if any(
                item.get("code") and item["code"] not in product_codes
                for item in relationship["items"]
            ):
                raise CommandError(
                    "Every linked MES component must be a catalogue item."
                )

        selected_parents = set(options["relationship_parent"])
        if selected_parents:
            self._sync_selected_relationships(
                catalogue,
                selected_parents,
                skip_images=options["skip_images"],
            )
            return

        with transaction.atomic():
            category, _ = Category.objects.update_or_create(
                slug=CATEGORY_SLUG,
                defaults={
                    "name": "Semen Analyzers (SQA)",
                    "menu_label": "Semen Analyzers (SQA)",
                    "description": (
                        "Medical Electronic Systems automated semen-analysis "
                        "equipment for clinical and andrology laboratories."
                    ),
                    "icon": "microscope",
                    "display_order": 13,
                    "is_active": True,
                },
            )
            subcategories = {}
            for index, definition in enumerate(catalogue["subcategories"]):
                subcategory, _ = ProductSubcategory.objects.update_or_create(
                    category=category,
                    slug=definition["slug"],
                    defaults={
                        "name": definition["name"],
                        "description": definition["description"],
                        "display_order": index,
                        "is_active": True,
                    },
                )
                subcategories[definition["slug"]] = subcategory
            ProductSubcategory.objects.filter(category=category).exclude(
                slug__in=EXPECTED_SUBCATEGORIES
            ).update(is_active=False)
            partner, _ = Partner.objects.get_or_create(
                name=BRAND,
                defaults={
                    "website": "https://mes-global.com/",
                    "equipment_group": "laboratory",
                    "menu_label": "Medical Electronic System",
                    "menu_order": 3,
                    "is_active": True,
                },
            )
            partner.menu_categories.add(category)

            created_count = updated_count = image_count = 0
            imported_products = {}
            for definition in products:
                status = definition["status"]
                defaults = {
                    "category": category,
                    "subcategory": subcategories[definition["subcategory"]],
                    "name": definition["name"],
                    "slug": definition["slug"],
                    "brand": BRAND,
                    "short_description": definition["short_description"],
                    "description": definition["description"],
                    "specifications": self._specifications(definition),
                    "price": None,
                    "availability": (
                        "unavailable" if status == "discontinued" else "on_request"
                    ),
                    "is_featured": False,
                    "is_active": True,
                    "is_catalogue_listing": (
                        definition["code"] in listing_codes
                    ),
                }
                product, was_created = Product.objects.update_or_create(
                    product_code=definition["code"],
                    defaults=defaults,
                )
                created_count += int(was_created)
                updated_count += int(not was_created)
                imported_products[definition["code"]] = product
                if not options["skip_images"]:
                    image_count += int(self._attach_image(
                        product,
                        definition,
                        replace=options["replace_images"],
                    ))

            Product.objects.filter(
                category=category,
                brand__iexact=BRAND,
            ).exclude(product_code__in=product_codes).update(is_active=False)

            ProductRelatedItem.objects.filter(
                parent_product__category=category,
                parent_product__brand__iexact=BRAND,
            ).delete()
            relationship_count = 0
            for relationship in catalogue.get("relationships", []):
                parent = imported_products[relationship["parent_code"]]
                for order, item in enumerate(relationship["items"]):
                    child = imported_products.get(item.get("code", ""))
                    related_item = ProductRelatedItem.objects.create(
                        parent_product=parent,
                        child_product=child,
                        name=item.get("name") or child.name,
                        description=(
                            item.get("description")
                            or (child.description if child else "")
                        ),
                        relationship_type=item.get("type", "included"),
                        display_order=order,
                    )
                    if not options["skip_images"] and item.get("image_filename"):
                        image_count += int(self._attach_related_image(
                            related_item,
                            item["image_filename"],
                        ))
                    relationship_count += 1

        self.stdout.write(self.style.SUCCESS(
            "MES products catalogue complete: "
            f"{created_count} created, {updated_count} updated; "
            f"{expected_count} official items across 5 families and "
            f"{relationship_count} nested relationships verified; "
            f"{image_count} official images stored."
        ))

    def _sync_selected_relationships(
        self,
        catalogue,
        selected_parents,
        *,
        skip_images,
    ):
        relationships = {
            relationship["parent_code"]: relationship
            for relationship in catalogue.get("relationships", [])
            if relationship["parent_code"] in selected_parents
        }
        unknown = selected_parents - set(relationships)
        if unknown:
            raise CommandError(
                "Unknown MES relationship parent(s): " + ", ".join(sorted(unknown))
            )

        downloaded_images = {}
        if not skip_images:
            for relationship in relationships.values():
                for item in relationship["items"]:
                    source_url = item.get("source_image_url")
                    if source_url and source_url not in downloaded_images:
                        downloaded_images[source_url] = self._download_image(source_url)

        product_codes = selected_parents | {
            item["code"]
            for relationship in relationships.values()
            for item in relationship["items"]
            if item.get("code")
        }
        products = Product.objects.in_bulk(product_codes, field_name="product_code")
        missing = product_codes - set(products)
        if missing:
            raise CommandError(
                "Missing existing MES product(s): " + ", ".join(sorted(missing))
            )

        updated_count = image_count = 0
        with transaction.atomic():
            for parent_code, relationship in relationships.items():
                parent = products[parent_code]
                retained_ids = []
                for order, item in enumerate(relationship["items"]):
                    child = products[item["code"]]
                    related_item = ProductRelatedItem.objects.filter(
                        parent_product=parent,
                        child_product=child,
                    ).first()
                    if related_item is None:
                        related_item = ProductRelatedItem(
                            parent_product=parent,
                            child_product=child,
                        )
                    related_item.name = item.get("name") or child.name
                    related_item.description = (
                        item.get("description") or child.description
                    )
                    related_item.relationship_type = item.get(
                        "type", "included"
                    )
                    related_item.display_order = order
                    related_item.save()
                    retained_ids.append(related_item.pk)
                    updated_count += 1

                    source_url = item.get("source_image_url")
                    if not skip_images and source_url:
                        if related_item.image:
                            related_item.image.delete(save=False)
                        related_item.image.save(
                            f"{parent.slug}/{item['image_filename']}",
                            ContentFile(downloaded_images[source_url]),
                            save=True,
                        )
                        if not related_item.image.storage.exists(
                            related_item.image.name
                        ):
                            raise CommandError(
                                "Stored MES relationship image is unavailable: "
                                f"{related_item.image.name}"
                            )
                        image_count += 1

                ProductRelatedItem.objects.filter(
                    parent_product=parent,
                ).exclude(pk__in=retained_ids).delete()

        self.stdout.write(self.style.SUCCESS(
            "MES Included & Related correction complete: "
            f"{updated_count} verified rows across {len(relationships)} parent "
            f"products; {image_count} official images stored."
        ))

    @staticmethod
    def _download_image(source_url):
        request = Request(
            source_url,
            headers={"User-Agent": "Somlab MES catalogue importer/1.0"},
        )
        try:
            with urlopen(request, timeout=30) as response:
                if response.status != 200:
                    raise CommandError(
                        f"MES image returned HTTP {response.status}: {source_url}"
                    )
                content_type = response.headers.get_content_type()
                if not content_type.startswith("image/"):
                    raise CommandError(
                        f"MES image returned {content_type}: {source_url}"
                    )
                content = response.read()
            Image.open(BytesIO(content)).verify()
        except (OSError, UnidentifiedImageError) as exc:
            raise CommandError(
                f"Unable to verify official MES image {source_url}: {exc}"
            ) from exc
        return content

    @staticmethod
    def _catalogue():
        if not DATA_FILE.exists():
            raise CommandError(f"Missing bundled catalogue data: {DATA_FILE}")
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))

    @staticmethod
    def _specifications(definition):
        lines = [
            f"{label}: {value}"
            for label, value in definition.get("specifications", [])
        ]
        if not lines:
            return ""
        lines.append(f"Official source: {definition['source_url']}")
        return "\n".join(lines)

    @staticmethod
    def _attach_image(product, definition, *, replace):
        image_filename = definition.get("image_filename")
        if not image_filename or (product.image and not replace):
            return False
        image_path = DATA_DIRECTORY / "images" / image_filename
        if not image_path.is_file():
            raise CommandError(f"Missing bundled official MES image: {image_path}")
        product.image = ContentFile(image_path.read_bytes(), name=image_filename)
        product.save(update_fields=["image"])
        return True

    @staticmethod
    def _attach_related_image(related_item, image_filename):
        image_path = DATA_DIRECTORY / "images" / image_filename
        if not image_path.is_file():
            raise CommandError(f"Missing bundled official MES image: {image_path}")
        related_item.image = ContentFile(
            image_path.read_bytes(),
            name=f"{related_item.parent_product.slug}/{image_filename}",
        )
        related_item.save(update_fields=["image"])
        return True
