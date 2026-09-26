from django.core.files.storage import InMemoryStorage
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.models import Product
from catalog.navigation import product_navigation_groups


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
)
class HelicAbtReaderTests(TestCase):
    def setUp(self):
        call_command("import_helic_abt_reader", verbosity=0)

    def test_import_is_idempotent_and_uses_own_category(self):
        call_command("import_helic_abt_reader", verbosity=0)
        product = Product.objects.get(product_code="AMA-HELIC-ABT-READER")
        self.assertEqual(Product.objects.filter(
            product_code="AMA-HELIC-ABT-READER"
        ).count(), 1)
        self.assertEqual(product.brand, "AMA Helic UBT Reader")
        self.assertEqual(product.category.slug, "ama-helic-ubt-reader")
        self.assertEqual(product.availability, "on_request")
        self.assertNotIn(product.category.slug, {
            "chemistry", "hematology", "immunoassay",
        })

    def test_catalogue_search_filter_and_detail(self):
        product = Product.objects.get(product_code="AMA-HELIC-ABT-READER")
        self.assertContains(self.client.get(reverse("product_list")), product.name)
        self.assertContains(
            self.client.get(reverse("product_list"), {"q": "HELIC® ABT"}),
            product.name,
        )
        self.assertContains(
            self.client.get(
                reverse("product_list"),
                {"brand": "ama-helic-ubt-reader"},
            ),
            product.name,
        )
        detail = self.client.get(product.get_absolute_url())
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Available on request")
        self.assertContains(detail, "Sensitivity: 95%")

    def test_urea_breath_test_menu_expands_to_reader_detail_only(self):
        product = Product.objects.get(product_code="AMA-HELIC-ABT-READER")
        laboratory = next(group for group in product_navigation_groups()
                          if group["slug"] == "laboratory")
        urea = next(item for item in laboratory["flat_items"]
                    if item["label"] == "Urea Breath Test")
        self.assertEqual(urea["children"], [{
            "label": "HELIC® ABT Reader",
            "url": product.get_absolute_url(),
        }])
