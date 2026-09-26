from django.core.files.storage import InMemoryStorage
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from catalog.models import Category, Product, ProductSubcategory
from core.models import Partner


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
)
class EschweilerImportTests(TestCase):
    def test_import_is_complete_public_and_idempotent(self):
        call_command("import_eschweiler_products", verbosity=0)
        call_command("import_eschweiler_products", verbosity=0)

        products = Product.objects.filter(brand="Eschweiler ABG")
        self.assertEqual(products.count(), 12)
        self.assertTrue(products.filter(product_code="ESCH-MP-CALPACK").exists())
        self.assertTrue(products.filter(product_code="ESCH-MP-SENSORS").exists())
        self.assertTrue(products.filter(product_code="ESCH-MP-TECHNICAL-DATA").exists())
        self.assertTrue(products.filter(product_code="ESCH-CL2-CAL").exists())
        self.assertTrue(products.filter(product_code="ESCH-CL2-OPERATION").exists())
        self.assertTrue(products.filter(product_code="ESCH-CL2-TECHNICAL-DATA").exists())
        self.assertFalse(products.filter(product_code__contains="-SENSOR-").exists())
        for product in products:
            with self.subTest(product=product.name):
                self.assertEqual(product.category.slug, "eschweiler-abg")
                self.assertIn(
                    product.subcategory.slug,
                    {"modular-pro", "combi-line-2"},
                )
                self.assertEqual(product.availability, "on_request")
                detail = self.client.get(product.get_absolute_url())
                self.assertEqual(detail.status_code, 200)
                self.assertContains(detail, product.product_code)
                self.assertContains(detail, "Available on request")

        filtered = self.client.get(
            reverse("product_list"),
            {"brand": "eschweiler-abg"},
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(list(filtered.context["products"]), list(products))
        self.assertContains(filtered, "modular pro")
        self.assertContains(filtered, "combi line 2")

        category = Category.objects.get(slug="eschweiler-abg")
        category_page = self.client.get(category.get_absolute_url())
        self.assertContains(category_page, "modular pro")
        self.assertContains(category_page, "combi line 2")
        self.assertContains(category_page, "calibration")
        self.assertNotEqual(category.slug, "chemistry")
        self.assertFalse(products.filter(category__slug="chemistry").exists())

        search = self.client.get(reverse("product_list"), {"q": "modular pro"})
        self.assertContains(search, "modular pro")

        partner = Partner.objects.get(name="Eschweiler ABG")
        self.assertEqual(partner.equipment_group, "laboratory")
        self.assertTrue(partner.is_active)
        self.assertEqual(
            list(partner.menu_categories.values_list("slug", flat=True)),
            ["eschweiler-abg"],
        )

    def test_navigation_expands_eschweiler_to_its_two_system_groups(self):
        call_command("import_eschweiler_products", verbosity=0)
        from catalog.navigation import product_navigation_groups

        laboratory = next(
            group for group in product_navigation_groups()
            if group["slug"] == "laboratory"
        )
        eschweiler = next(
            manufacturer for manufacturer in laboratory["manufacturers"]
            if manufacturer["partner"].name == "Eschweiler ABG"
        )
        category = Category.objects.get(slug="eschweiler-abg")
        self.assertEqual(eschweiler["categories"], [
            {
                "label": "modular pro",
                "url": ProductSubcategory.objects.get(
                    category=category,
                    slug="modular-pro",
                ).get_absolute_url(),
            },
            {
                "label": "combi line 2",
                "url": ProductSubcategory.objects.get(
                    category=category,
                    slug="combi-line-2",
                ).get_absolute_url(),
            },
        ])

        response = self.client.get(reverse("home"))
        content = response.content.decode()
        start = content.index('id="laboratory-menu-heading"')
        end = content.index('id="medical-equipment-menu-heading"', start)
        laboratory_menu = content[start:end]
        self.assertIn(
            '<span>Eschweiler ABG</span>',
            laboratory_menu,
        )
        self.assertIn(
            f'href="{ProductSubcategory.objects.get(category=category, slug="modular-pro").get_absolute_url()}"><span>Modular Pro</span>',
            laboratory_menu,
        )
        self.assertIn(
            f'href="{ProductSubcategory.objects.get(category=category, slug="combi-line-2").get_absolute_url()}"><span>Combi Line 2</span>',
            laboratory_menu,
        )
        self.assertIn(
            'aria-controls="laboratory-menu-eschweiler-abg"',
            laboratory_menu,
        )

    def test_scoped_card_image_fit_excludes_placeholders(self):
        call_command("import_eschweiler_products", verbosity=0)
        category = Category.objects.get(slug="eschweiler-abg")

        expected = {"modular-pro": 5, "combi-line-2": 4}
        for slug, image_count in expected.items():
            with self.subTest(subcategory=slug):
                subcategory = ProductSubcategory.objects.get(
                    category=category,
                    slug=slug,
                )
                response = self.client.get(subcategory.get_absolute_url())
                self.assertEqual(response.status_code, 200)
                content = response.content.decode()
                self.assertEqual(
                    content.count("eschweiler-product-image-fit"),
                    image_count,
                )
                self.assertContains(response, 'class="product-placeholder"')

    def test_scoped_official_image_audit_preserves_partner_and_other_fields(self):
        from catalog.management.commands.import_eschweiler_products import (
            ASSET_DIR,
        )

        call_command("import_eschweiler_products", verbosity=0)
        partner = Partner.objects.get(name="Eschweiler ABG")
        partner.country = "Protected partner value"
        partner.save(update_fields=["country"])
        product = Product.objects.get(product_code="ESCH-MP-TOUCH")
        product.price = "123.45"
        product.description = "Protected description"
        product.save(update_fields=["price", "description"])
        official_bytes = (ASSET_DIR / "modular-touchscreen.png").read_bytes()

        with patch(
            "catalog.management.commands.import_eschweiler_products."
            "Command._download_official_image",
            return_value=official_bytes,
        ):
            call_command(
                "import_eschweiler_products",
                audit_official_images=True,
                verbosity=0,
            )

        product.refresh_from_db()
        partner.refresh_from_db()
        self.assertEqual(product.name, "touchscreen")
        self.assertEqual(product.subcategory.slug, "modular-pro")
        self.assertEqual(str(product.price), "123.45")
        self.assertEqual(product.description, "Protected description")
        self.assertEqual(partner.country, "Protected partner value")
        self.assertTrue(product.image)
        self.assertTrue(product.source_image)
        with product.image.storage.open(product.image.name, "rb") as stored:
            self.assertEqual(stored.read(), official_bytes)
        lan = Product.objects.get(product_code="ESCH-MP-LAN")
        self.assertFalse(lan.image)
        technical = Product.objects.get(product_code="ESCH-MP-TECHNICAL-DATA")
        self.assertFalse(technical.image)
        self.assertFalse(technical.source_image)
        self.assertEqual(
            Product.objects.filter(
                brand="Eschweiler ABG",
                subcategory__slug="modular-pro",
            ).count(),
            7,
        )
        self.assertEqual(
            Product.objects.filter(
                brand="Eschweiler ABG",
                subcategory__slug="combi-line-2",
            ).count(),
            5,
        )

    def test_scoped_audit_removes_obsolete_parameter_products(self):
        from catalog.management.commands.import_eschweiler_products import (
            ASSET_DIR,
        )

        call_command("import_eschweiler_products", verbosity=0)
        category = Category.objects.get(slug="eschweiler-abg")
        group = ProductSubcategory.objects.get(
            category=category,
            slug="combi-line-2",
        )
        sensor = Product.objects.create(
            category=category,
            subcategory=group,
            name="pH Sensor",
            slug="obsolete-combi-line-2-ph-sensor",
            brand="Eschweiler ABG",
            product_code="ESCH-CL2-SENSOR-PH",
            short_description="Obsolete parameter breakdown.",
            description="Obsolete parameter breakdown.",
        )
        sensor.image.save(
            "incorrect-shared-sensor.png",
            ContentFile(b"incorrect shared group image"),
        )
        official_bytes = (ASSET_DIR / "modular-touchscreen.png").read_bytes()

        with patch(
            "catalog.management.commands.import_eschweiler_products."
            "Command._download_official_image",
            return_value=official_bytes,
        ):
            call_command(
                "import_eschweiler_products",
                audit_official_images=True,
                verbosity=0,
            )

        self.assertFalse(
            Product.objects.filter(product_code="ESCH-CL2-SENSOR-PH").exists()
        )
