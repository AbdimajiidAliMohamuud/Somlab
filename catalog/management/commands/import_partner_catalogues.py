import json
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify

from catalog.models import Category, Product, ProductSubcategory
from core.models import Partner


DATA_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "partner_catalogues"
    / "products.json"
)

PARTNER_CATEGORY_DEFINITIONS = {
    "DIAGNOSTICS i.n.c.": (
        "diagnostics", "DIAGNOSTICS",
        "Official DIAGNOSTICS microbiology identification, screening and susceptibility-testing products.",
        "test-tube", 103,
    ),
    "Bioer Technology": (
        "bioer", "Bioer",
        "Official Bioer molecular diagnostics, laboratory instruments and consumables.",
        "dna", 104,
    ),
    "Biosan": (
        "biosan", "Biosan",
        "Official Biosan laboratory instruments and life-science equipment.",
        "microscope", 105,
    ),
    "Turklab": (
        "turklab", "TURKLAB",
        "Official TURKLAB rapid diagnostic and blood-grouping products.",
        "test-tube", 106,
    ),
    "GeneProof": (
        "geneproof", "GeneProof",
        "Official GeneProof molecular diagnostic assays, extraction products and systems.",
        "dna", 107,
    ),
}

PARTNERS = {
    "DIAGNOSTICS i.n.c.": ("Slovakia", "http://www.diagnostics.sk/?lang=en"),
    "Bioer Technology": ("China", "https://en.bioer.com"),
    "Biosan": ("Latvia", "https://biosan.lv"),
    "Turklab": ("Turkey", "https://www.turklab.com.tr/en"),
    "GeneProof": ("Czech Republic", "https://www.geneproof.com"),
}


class Command(BaseCommand):
    help = "Import five verified official partner catalogues without importing images."

    def handle(self, *args, **options):
        raise CommandError(
            "This importer is retired because the five partner catalogues "
            "were intentionally removed from Products & Solutions."
        )
        if not DATA_FILE.exists():
            raise CommandError(f"Source snapshot is missing: {DATA_FILE}")
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        products = payload.get("products", [])
        if not products:
            raise CommandError("The partner catalogue snapshot contains no products.")

        duplicate_codes = self._duplicates(item["code"] for item in products)
        duplicate_products = self._duplicates(
            (item["partner"].casefold(), item["name"].casefold())
            for item in products
        )
        if duplicate_codes or duplicate_products:
            raise CommandError(
                "Snapshot uniqueness check failed: "
                f"codes={duplicate_codes}, products={duplicate_products}"
            )
        if {item["column"] for item in products} != {"laboratory"}:
            raise CommandError("Every verified item must resolve to the Laboratory column.")

        with transaction.atomic():
            categories = self._categories(products)
            subcategories = self._subcategories(products, categories)
            self._partners()

            created = updated = 0
            imported_by_brand = defaultdict(set)
            for definition in products:
                code = definition["code"]
                imported_by_brand[definition["partner"]].add(code)
                product = Product.objects.filter(
                    Q(product_code=code)
                    | Q(
                        brand__iexact=definition["partner"],
                        name__iexact=definition["name"],
                    )
                ).first()
                defaults = self._defaults(
                    definition,
                    categories[definition["partner"]],
                    subcategories[(definition["partner"], definition["subcategory"])],
                )
                if product is None:
                    product = Product.objects.create(
                        slug=self._available_slug(definition),
                        product_code=code,
                        **defaults,
                    )
                    created += 1
                else:
                    for field, value in {"product_code": code, **defaults}.items():
                        setattr(product, field, value)
                    # Deliberately omit image/source_image and gallery records:
                    # rerunning this command must preserve manual uploads.
                    product.save(update_fields=[
                        "product_code", *defaults.keys(), "updated_at"
                    ])
                    updated += 1

            for brand, codes in imported_by_brand.items():
                Product.objects.filter(brand__iexact=brand).exclude(
                    product_code__in=codes
                ).update(is_active=False)

        self.stdout.write(self.style.SUCCESS(
            f"Partner catalogues complete: {created} created, {updated} updated, "
            f"{len(products)} verified products; no images imported or changed."
        ))

    @staticmethod
    def _duplicates(values):
        seen = set()
        return sorted({value for value in values if value in seen or seen.add(value)})

    @staticmethod
    def _categories(products):
        brands = {item["partner"] for item in products}
        unknown = brands - PARTNER_CATEGORY_DEFINITIONS.keys()
        if unknown:
            raise CommandError(f"Unknown catalogue partners: {sorted(unknown)}")
        slugs = {PARTNER_CATEGORY_DEFINITIONS[brand][0] for brand in brands}
        categories = {
            category.slug: category
            for category in Category.objects.filter(slug__in=slugs)
        }
        result = {}
        for brand in brands:
            slug, name, description, icon, order = PARTNER_CATEGORY_DEFINITIONS[brand]
            category = categories.get(slug)
            if category is None:
                category = Category.objects.create(
                    name=name, slug=slug, description=description, icon=icon,
                    display_order=order, is_active=True,
                )
            else:
                category.name = name
                category.description = description
                category.icon = icon
                category.display_order = order
                category.is_active = True
                category.save(update_fields=[
                    "name", "description", "icon", "display_order", "is_active",
                ])
            result[brand] = category
        return result

    @staticmethod
    def _subcategories(products, categories):
        result = {}
        positions = defaultdict(int)
        for item in products:
            key = (item["partner"], item["subcategory"])
            if key in result:
                continue
            category = categories[item["partner"]]
            slug = slugify(item["subcategory"])[:80]
            result[key], _ = ProductSubcategory.objects.update_or_create(
                category=category,
                slug=slug,
                defaults={
                    "name": item["subcategory"],
                    "description": "",
                    "display_order": positions[item["partner"]],
                    "is_active": True,
                },
            )
            positions[item["partner"]] += 1
        return result

    @staticmethod
    def _partners():
        for order, (name, (country, website)) in enumerate(PARTNERS.items(), 20):
            partner, _ = Partner.objects.update_or_create(
                name=name,
                defaults={
                    "country": country,
                    "website": website,
                    "description": f"Official {name} laboratory catalogue partner.",
                    # These catalogues are exposed as dedicated Laboratory
                    # categories, so no duplicate manufacturer node is needed.
                    "equipment_group": "",
                    "menu_order": order,
                    "is_active": True,
                },
            )
            partner.menu_categories.clear()

    @staticmethod
    def _defaults(definition, category, subcategory):
        description = definition["description"].strip()
        specifications = list(definition.get("specifications", []))
        specifications.append(f"Official source: {definition['source_url']}")
        return {
            "category": category,
            "subcategory": subcategory,
            "name": definition["name"],
            "brand": definition["partner"],
            "short_description": description[:240],
            "description": description,
            "specifications": "\n".join(specifications),
            "price": None,
            "availability": "on_request",
            "is_featured": False,
            "is_active": True,
            "is_catalogue_listing": True,
        }

    @staticmethod
    def _available_slug(definition):
        base = slugify(f"{definition['partner']}-{definition['name']}")[:48]
        candidate = base
        suffix = 2
        while Product.objects.filter(slug=candidate).exists():
            candidate = f"{base[:44]}-{suffix}"
            suffix += 1
        return candidate
