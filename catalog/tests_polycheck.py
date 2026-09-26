from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from catalog.polycheck_source import parse_polycheck_catalogue


class PolycheckSourceParserTests(SimpleTestCase):
    def test_extracts_verified_product_components_variants_and_image(self):
        source = '''
        <div id="table_id_3023">
          <table><tr data-title="AI-STD" data-product_id="2845"
            data-href="https://polycheck.de/product/ai-std-2/"
            data-product_variations='[{"attributes":{"attribute_size":"24-Kit"},"sku":"05012040","image":{"full_src":"https://polycheck.de/ai-std.jpg"}}]'>
            <td><div class="wpt_short_description"><table>
              <tr><td>Ro/SS-A 60</td></tr><tr><td>La/SS-B</td></tr>
            </table></div></td>
          </tr></table>
        </div>
        '''
        products = parse_polycheck_catalogue(source)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["group"], "Autoimmune")
        self.assertEqual(products[0]["components"], ["Ro/SS-A 60", "La/SS-B"])
        self.assertEqual(products[0]["variants"], [{"name": "24-Kit", "sku": "05012040"}])
        self.assertEqual(products[0]["image_url"], "https://polycheck.de/ai-std.jpg")


class PolycheckImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("import_polycheck_products", "--skip-images")

    def test_imports_complete_grouped_catalogue_idempotently(self):
        from catalog.models import Category, Product
        from core.models import Partner

        category = Category.objects.get(slug="polycheck")
        self.assertEqual(
            list(category.subcategories.values_list("name", flat=True)),
            ["Autoimmune", "Allergy", "Veterinary"],
        )
        self.assertEqual(Product.objects.filter(brand="Polycheck", is_active=True).count(), 66)
        partner = Partner.objects.get(name="Polycheck")
        self.assertEqual(list(partner.menu_categories.all()), [category])

        call_command("import_polycheck_products", "--skip-images")
        self.assertEqual(Product.objects.filter(brand="Polycheck", is_active=True).count(), 66)

    def test_catalogue_and_product_detail_use_existing_pages(self):
        from catalog.models import Product

        catalogue = self.client.get(reverse("category_detail", args=["polycheck"]))
        self.assertEqual(catalogue.status_code, 200)
        self.assertContains(catalogue, "Autoimmune")
        self.assertContains(catalogue, "Allergy")
        self.assertContains(catalogue, "Veterinary")

        product = Product.objects.get(slug="polycheck-ai-std")
        detail = self.client.get(product.get_absolute_url())
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "AI-STD")
        self.assertContains(detail, "Ro/SS-A 60")
