from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from catalog.models import Category, Product
from catalog.navigation import product_navigation_groups
from core.models import Partner


REMOVED_CATEGORY_SLUGS = {
    "molecular-diagnostics",
    "laboratory-equipment",
    "laboratory-consumables",
    "diagnostics",
    "bioer",
    "biosan",
    "turklab",
    "geneproof",
}

REMOVED_BRANDS = {
    "DIAGNOSTICS i.n.c.",
    "Bioer Technology",
    "Biosan",
    "Turklab",
    "GeneProof",
}


class RemovedPartnerCatalogueTests(TestCase):
    def test_removed_catalogue_records_are_absent_but_partners_are_preserved(self):
        self.assertFalse(Category.objects.filter(
            slug__in=REMOVED_CATEGORY_SLUGS,
        ).exists())
        self.assertFalse(Product.objects.filter(brand__in=REMOVED_BRANDS).exists())
        partners = Partner.objects.filter(name__in=REMOVED_BRANDS)
        self.assertEqual(partners.count(), 5)
        self.assertFalse(partners.exclude(equipment_group="").exists())
        self.assertFalse(partners.filter(menu_categories__isnull=False).exists())

    def test_removed_entries_are_absent_from_product_navigation(self):
        laboratory = next(
            group for group in product_navigation_groups()
            if group["slug"] == "laboratory"
        )
        destinations = {
            item["url"] for item in laboratory["flat_items"]
        }
        for slug in REMOVED_CATEGORY_SLUGS:
            self.assertNotIn(f"/products/category/{slug}/", destinations)

    def test_retired_importer_cannot_recreate_entries(self):
        with self.assertRaisesMessage(CommandError, "intentionally removed"):
            call_command("import_partner_catalogues", verbosity=0)
