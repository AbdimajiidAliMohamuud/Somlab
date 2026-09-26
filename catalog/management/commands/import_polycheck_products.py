import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from catalog.models import Category, Product, ProductSubcategory, ProductVariant
from catalog.polycheck_source import (
    POLYCHECK_INDEX_URL,
    fetch_polycheck_catalogue,
    polycheck_ssl_context,
)
from core.models import Partner


BRAND = "Polycheck"
DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "polycheck" / "products.json"
GROUPS = (
    (
        "Autoimmune",
        "autoimmune",
        "Polycheck® panels for autoimmune screening and organ-related autoaggression.",
    ),
    (
        "Allergy",
        "allergy",
        "Polycheck® allergen-specific IgE panels for inhalation, food, paediatric and component testing.",
    ),
    (
        "Veterinary",
        "veterinary",
        "Polycheck® veterinary diagnostic panels customized for dogs, cats and horses.",
    ),
)


class Command(BaseCommand):
    help = "Import the verified official Polycheck product catalogue."

    def add_arguments(self, parser):
        parser.add_argument("--skip-images", action="store_true")
        parser.add_argument("--replace-images", action="store_true")
        parser.add_argument(
            "--refresh-source",
            action="store_true",
            help="Refresh the bundled source snapshot from Polycheck before importing.",
        )

    def handle(self, *args, **options):
        catalogue = self._catalogue(options["refresh_source"])
        if len(catalogue) != 66:
            raise CommandError(
                f"Expected 66 official Polycheck products, received {len(catalogue)}; import stopped."
            )

        with transaction.atomic():
            category, _ = Category.objects.update_or_create(
                slug="polycheck",
                defaults={
                    "name": BRAND,
                    "menu_label": BRAND,
                    "description": (
                        "Polycheck® multiparameter in vitro diagnostic panels for allergy, "
                        "autoimmune and veterinary testing."
                    ),
                    "icon": "test-tube",
                    "display_order": 8,
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
                        "description": description,
                        "display_order": order,
                        "is_active": True,
                    },
                )

            partner, _ = Partner.objects.update_or_create(
                name=BRAND,
                defaults={
                    "country": "Germany",
                    "website": POLYCHECK_INDEX_URL,
                    "description": (
                        "German manufacturer of multiparameter in vitro diagnostic "
                        "panels for allergy, autoimmune and veterinary testing."
                    ),
                    "equipment_group": "laboratory",
                    "menu_label": BRAND,
                    "menu_order": 2,
                    "is_active": True,
                },
            )
            partner.menu_categories.set([category])

            created = updated = imaged = 0
            image_cache = {}
            for definition in catalogue:
                code = self._product_code(definition)
                defaults = self._product_defaults(definition, category, subcategories)
                item, was_created = Product.objects.update_or_create(
                    product_code=code,
                    defaults=defaults,
                )
                created += int(was_created)
                updated += int(not was_created)
                self._replace_variants(item, definition["variants"])

                if (
                    not options["skip_images"]
                    and definition.get("image_url")
                    and (options["replace_images"] or not item.image)
                ):
                    image_url = definition["image_url"]
                    assigned_image = False
                    if image_url in image_cache:
                        cached_image = image_cache[image_url]
                        if cached_image:
                            image_name, source_name = cached_image
                            Product.objects.filter(pk=item.pk).update(
                                image=image_name,
                                source_image=source_name,
                            )
                            assigned_image = True
                    else:
                        content = self._download_image(image_url)
                        if content:
                            # Assign the uncommitted upload before saving so the
                            # shared Product.save() normalization pipeline runs.
                            item.image = content
                            item.save()
                            image_cache[image_url] = (
                                item.image.name,
                                item.source_image.name,
                            )
                            assigned_image = True
                        else:
                            image_cache[image_url] = None
                    if assigned_image:
                        imaged += 1

            # Remove the original demo-only Polycheck reader from the public
            # catalogue; it is not present in the verified manufacturer source.
            Product.objects.filter(
                product_code="SL-EL-096",
                name="ELISA Microplate Reader ER-96",
                brand__iexact=BRAND,
            ).update(is_active=False)

        self.stdout.write(self.style.SUCCESS(
            f"Polycheck catalogue complete: {created} created, {updated} updated, "
            f"{imaged} product image assignments; {len(catalogue)} verified products."
        ))

    def _catalogue(self, refresh):
        if refresh:
            products = fetch_polycheck_catalogue()
            DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            DATA_FILE.write_text(
                json.dumps(
                    {"source": POLYCHECK_INDEX_URL, "products": products},
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            return products
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))["products"]

    @staticmethod
    def _product_code(definition):
        return (
            next((variant["sku"] for variant in definition["variants"] if variant["sku"]), "")
            or definition.get("row_sku")
            or f"POLYCHECK-{definition['source_id']}"
        )

    @staticmethod
    def _product_defaults(definition, category, subcategories):
        group = definition["group"]
        component_count = len(definition["components"])
        short_description = (
            f"Polycheck® {group.lower()} multiparameter immunoassay panel"
            + (f" with {component_count} officially listed targets." if component_count else ".")
        )
        if group == "Allergy":
            description = (
                "A Polycheck® in vitro diagnostic panel for quantitative determination "
                "of allergen-specific IgE in blood samples."
            )
        elif group == "Autoimmune":
            description = (
                "A Polycheck® in vitro diagnostic panel for autoimmune screening using "
                "disease-related immunoglobulin targets in blood samples."
            )
        else:
            description = (
                "A Polycheck® veterinary diagnostic panel developed for characteristic "
                "allergy testing requirements in companion animals."
            )
        specifications = [f"Product group: {group}"]
        if definition["components"]:
            specifications.append("Panel components:")
            specifications.extend(f"  {component}" for component in definition["components"])
        if definition["variants"]:
            specifications.append("Available kit formats:")
            for variant in definition["variants"]:
                label = variant["name"]
                if variant["sku"]:
                    label = f"{label} — SKU {variant['sku']}"
                specifications.append(f"  {label}")
        return {
            "category": category,
            "subcategory": subcategories[group],
            "name": definition["name"],
            "slug": f"polycheck-{slugify(definition['name'])}",
            "brand": BRAND,
            "short_description": short_description[:240],
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
                name=variant["name"],
                model_number=variant["sku"],
                display_order=index,
            )
            for index, variant in enumerate(variants)
            if variant["name"] or variant["sku"]
        ])

    def _download_image(self, image_url):
        try:
            request = Request(
                image_url,
                headers={"User-Agent": "Somlab catalogue importer/1.0"},
            )
            with urlopen(
                request,
                timeout=45,
                context=polycheck_ssl_context(),
            ) as response:
                data = response.read()
            if not data:
                return None
            filename = Path(urlparse(image_url).path).name or "polycheck-product.jpg"
            return ContentFile(data, name=filename)
        except OSError as error:
            self.stderr.write(self.style.WARNING(
                f"Could not import Polycheck image {image_url}: {error}"
            ))
            return None
