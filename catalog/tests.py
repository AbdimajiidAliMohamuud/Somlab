from django.test import TestCase
from django.core.management import call_command
from django.urls import reverse
from .models import (
    Category, Product, ProductMedia, ProductSubcategory, ProductVariant,
)
from .labels import catalogue_display_label
from .scope import PUBLIC_CATEGORY_SLUGS
from .specifications import parse_specifications, render_specification_list


class CatalogTests(TestCase):
    NEW_MICROBIOLOGY_PRODUCTS = (
        ("SL-CC-226", "LabPro Information Manager", "labpro-information-manager"),
        ("SL-CC-227", "LabPro Connect", "labpro-connect"),
        (
            "SL-CC-228",
            "Copan WASP® DT: Walk-Away Specimen Processor",
            "copan-wasp-dt-walk-away-specimen-processor",
        ),
        (
            "SL-CC-229",
            "Copan WASPLab™ Microbiology Automation System",
            "copan-wasplab-microbiology-automation-system",
        ),
    )
    MICROBIOLOGY_PRODUCTS = (
        ("SL-CC-221", "ESβL plus Panels", "test-esbl-plus-panels"),
        ("SL-CC-220", "MICroSTREP plus Panels", "test-microstrep-plus-panels"),
        ("SL-CC-217", "MicroScan Conventional Panels", "test-microscan-conventional-panels"),
        ("SL-CC-218", "MicroScan Rapid ID panels", "test-microscan-rapid-id-panels"),
        ("SL-CC-219", "MicroScan Specialty ID Panels", "test-microscan-specialty-id-panels"),
        ("SL-CC-225", "Bruker MALDI Biotyper® System", "test-bruker-maldi-biotyper"),
        ("SL-CC-222", "DxM MicroScan WalkAway ID/AST System", "test-dxm-microscan-walkaway"),
        ("SL-CC-223", "MicroScan WalkAway plus System", "test-microscan-walkaway-plus"),
        ("SL-CC-224", "MicroScan autoSCAN-4 System", "test-microscan-autoscan-4"),
    )

    def setUp(self):
        self.category = Category.objects.get(slug="chemistry")
        self.product = Product.objects.create(
            category=self.category, name="Test Analyser", slug="test-analyser",
            product_code="TEST-1", short_description="Reliable testing.",
            description="A product description.", price="25.00",
        )

    def test_new_products_default_to_available_on_request(self):
        self.assertEqual(self.product.availability, "on_request")
        self.assertEqual(
            self.product.get_availability_display(),
            "Available on request",
        )

    def test_verified_microbiology_products_are_complete_and_use_standard_detail_page(self):
        expected_variants = {
            "SL-CC-226": [("LabPro Computer and Monitor", "B1018-510")],
            "SL-CC-227": [
                ("LabPro Connect Open System", "B1018-600"),
                ("LabPro Connect Closed System", "B1018-601"),
            ],
            "SL-CC-228": [("WASP Basic Instrument", "W086")],
            "SL-CC-229": [("WASPLab Server Rack Hardware", "10976013")],
        }

        for code, name, slug in self.NEW_MICROBIOLOGY_PRODUCTS:
            with self.subTest(product_code=code):
                product = Product.objects.get(product_code=code)
                self.assertEqual(product.name, name)
                self.assertEqual(product.slug, slug)
                self.assertEqual(product.category.slug, "microbiology")
                expected_brand = (
                    "COPAN" if code in {"SL-CC-228", "SL-CC-229"}
                    else "Beckman Coulter"
                )
                self.assertEqual(product.brand, expected_brand)
                self.assertTrue(product.short_description)
                self.assertTrue(product.description)
                self.assertTrue(product.specifications)
                self.assertEqual(product.availability, "on_request")
                self.assertTrue(product.is_active)
                self.assertFalse(product.is_featured)
                self.assertEqual(
                    list(product.variants.values_list("name", "model_number")),
                    expected_variants[code],
                )

                detail = self.client.get(product.get_absolute_url())
                self.assertEqual(detail.status_code, 200)
                self.assertTemplateUsed(detail, "catalog/product_detail.html")
                self.assertContains(detail, name)
                self.assertContains(detail, code)
                self.assertContains(detail, "Available on request")
                self.assertContains(detail, "Request price")
                self.assertContains(detail, "Inquiry")
                self.assertNotContains(detail, "Add to cart")
                self.assertContains(detail, "Product overview")
                self.assertContains(detail, "Product information")
                self.assertContains(detail, "Specifications")
                self.assertContains(detail, "Product variant / model")
                self.assertContains(detail, 'class="detail-placeholder"')

    def create_microbiology_products(self):
        category = Category.objects.get(slug="microbiology")
        return [
            Product.objects.create(
                category=category,
                name=name,
                slug=slug,
                product_code=product_code,
                brand="BECKMAN COULTER",
                short_description=f"{name} for microbiology workflows.",
                description=f"Detailed information about {name}.",
                availability="on_request",
            )
            for product_code, name, slug in self.MICROBIOLOGY_PRODUCTS
        ]

    def test_product_pages_render(self):
        self.assertEqual(self.client.get(reverse("product_list")).status_code, 200)
        self.assertEqual(self.client.get(self.category.get_absolute_url()).status_code, 200)
        detail = self.client.get(self.product.get_absolute_url())
        self.assertContains(detail, "Test Analyser")
        self.assertContains(detail, "Request price")
        self.assertNotContains(detail, "$25.00")
        for section_id, label in (("product-overview", "Overview"),):
            with self.subTest(product_section=section_id):
                self.assertContains(
                    detail,
                    f'href="#{section_id}" data-product-section-link>{label}',
                )
                self.assertContains(detail, f'id="{section_id}"')
        self.assertNotContains(detail, 'href="#product-specifications"')
        self.assertNotContains(detail, 'id="product-specifications"')
        self.assertNotContains(detail, "Specifications available on request")
        self.assertNotContains(detail, 'href="#product-downloads"')
        self.assertNotContains(detail, 'id="product-downloads"')
        self.assertNotContains(detail, "Documents available on request")

    def test_specifications_section_appears_from_product_data(self):
        self.product.specifications = "Method: Automated\nThroughput: 60 tests/hour"
        self.product.save(update_fields=["specifications"])

        detail = self.client.get(self.product.get_absolute_url())

        self.assertContains(
            detail,
            'href="#product-specifications" data-product-section-link>'
            "Specifications</a>",
        )
        self.assertContains(detail, 'id="product-specifications"')
        self.assertContains(detail, "Method: Automated")
        self.assertContains(detail, "Throughput: 60 tests/hour")

    def test_included_section_is_hidden_without_nested_items_or_siblings(self):
        solo_subcategory = ProductSubcategory.objects.create(
            category=self.category,
            name="Solo Products",
            slug="solo-products-test",
        )
        self.product.subcategory = solo_subcategory
        self.product.save(update_fields=["subcategory"])

        detail = self.client.get(self.product.get_absolute_url())

        self.assertNotContains(detail, 'href="#product-included"')
        self.assertNotContains(detail, 'id="product-included"')
        self.assertNotContains(detail, "No included items listed")

    def test_recommendations_are_siblings_from_the_same_subcategory(self):
        subcategory = ProductSubcategory.objects.create(
            category=self.category,
            name="Peer Products",
            slug="peer-products-test",
        )
        other_subcategory = ProductSubcategory.objects.create(
            category=self.category,
            name="Other Products",
            slug="other-products-test",
        )
        self.product.subcategory = subcategory
        self.product.save(update_fields=["subcategory"])
        sibling = Product.objects.create(
            category=self.category,
            subcategory=subcategory,
            name="Sibling Analyser",
            slug="sibling-analyser-test",
            product_code="SIBLING-TEST-1",
            short_description="A sibling product.",
            description="A sibling product.",
        )
        Product.objects.create(
            category=self.category,
            subcategory=other_subcategory,
            name="Different Group Analyser",
            slug="different-group-analyser-test",
            product_code="DIFFERENT-GROUP-TEST-1",
            short_description="Not a sibling product.",
            description="Not a sibling product.",
        )

        detail = self.client.get(self.product.get_absolute_url())

        self.assertEqual(detail.context["related"], [sibling])
        self.assertContains(detail, "YOU MAY ALSO NEED")
        self.assertContains(detail, sibling.name)
        self.assertNotContains(detail, "Different Group Analyser")

    def test_subcategories_use_shared_detail_page_and_only_show_assigned_products(self):
        subcategory = ProductSubcategory.objects.create(
            category=self.category,
            name="Routine Chemistry",
            slug="routine-chemistry",
            description="Routine chemistry systems and supplies.",
            image="subcategories/routine-chemistry.png",
        )
        self.product.subcategory = subcategory
        self.product.save(update_fields=["subcategory"])
        other = Product.objects.create(
            category=self.category,
            name="Other Chemistry Product",
            slug="other-chemistry-product",
            product_code="OTHER-CHEM-1",
            short_description="Another chemistry product.",
            description="Not assigned to the subcategory.",
        )

        self.assertEqual(
            subcategory.get_absolute_url(),
            reverse(
                "subcategory_detail",
                args=[self.category.slug, subcategory.slug],
            ),
        )
        response = self.client.get(subcategory.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalog/subcategory_detail.html")
        self.assertContains(response, "Routine Chemistry")
        self.assertContains(response, "Routine chemistry systems and supplies.")
        self.assertNotContains(response, 'class="section category-intro"')
        self.assertNotContains(response, "Open any product below")
        self.assertContains(response, "View products")
        self.assertContains(response, "routine-chemistry.png")
        self.assertContains(response, self.product.name)
        self.assertNotContains(response, other.name)
        self.assertEqual(response.context["products"], [self.product])

    def test_category_subcategory_links_open_the_shared_detail_page(self):
        subcategory = ProductSubcategory.objects.create(
            category=self.category,
            name="Routine Chemistry",
            slug="routine-chemistry",
        )
        self.product.subcategory = subcategory
        self.product.save(update_fields=["subcategory"])

        response = self.client.get(self.category.get_absolute_url())

        self.assertContains(
            response,
            f'href="{subcategory.get_absolute_url()}">Routine Chemistry</a>',
            count=2,
        )

    def test_product_gallery_displays_images_videos_and_variants(self):
        self.product.image = "products/test-main.jpg"
        self.product.save(update_fields=["image"])
        ProductMedia.objects.create(
            product=self.product,
            file="products/gallery/test-detail.jpg",
            media_type="image",
            display_order=0,
        )
        ProductMedia.objects.create(
            product=self.product,
            file="products/gallery/test-demo.mp4",
            media_type="video",
            display_order=1,
        )
        ProductVariant.objects.create(
            product=self.product,
            name="Test Analyser Compact",
            model_number="TA-100",
            display_order=0,
        )
        ProductVariant.objects.create(
            product=self.product,
            name="Test Analyser Plus",
            model_number="TA-200",
            display_order=1,
        )

        response = self.client.get(self.product.get_absolute_url())
        self.assertEqual(response.content.count(b"data-gallery-slide="), 3)
        self.assertEqual(response.content.count(b"data-gallery-thumb="), 3)
        self.assertContains(response, "<video controls", html=False)
        self.assertContains(response, "Product variant / model")
        self.assertContains(response, "Test Analyser Compact — TA-100")
        self.assertContains(response, "Test Analyser Plus — TA-200")

    def test_single_product_image_has_no_thumbnail_strip(self):
        self.product.image = "products/test-single.jpg"
        self.product.save(update_fields=["image"])
        response = self.client.get(self.product.get_absolute_url())
        self.assertEqual(response.content.count(b"data-gallery-slide="), 1)
        self.assertContains(response, 'class="product-gallery-slide is-image is-active"')
        self.assertNotContains(response, "data-gallery-thumb=")
        self.assertNotContains(response, "Product variant / model")

    def test_product_cards_use_the_shared_image_wrapper(self):
        self.product.image = "products/test-card.jpg"
        self.product.save(update_fields=["image"])

        response = self.client.get(reverse("product_list"))

        self.assertContains(response, 'class="product-image has-image"')
        self.assertNotContains(response, "zeiss-product-card")

    def test_unfiltered_catalogue_groups_each_product_once_by_category(self):
        response = self.client.get(reverse("product_list"))

        self.assertTrue(response.context["product_groups"])
        grouped_products = [
            product
            for group in response.context["product_groups"]
            for product in group["products"]
        ]
        self.assertEqual(len(grouped_products), len(response.context["products"]))
        self.assertEqual(
            {product.pk for product in grouped_products},
            {product.pk for product in response.context["products"]},
        )
        self.assertEqual(len(grouped_products), len({p.pk for p in grouped_products}))
        self.assertContains(response, 'class="catalog-category-groups"')

        filtered = self.client.get(reverse("product_list"), {"q": self.product.name})
        self.assertFalse(filtered.context["product_groups"])
        self.assertNotContains(filtered, 'class="catalog-category-groups"')

    def test_partner_catalogue_groups_each_product_once_by_category(self):
        from core.models import Partner

        Partner.objects.create(name="Acme Diagnostics", is_active=True)
        self.product.brand = "Acme Diagnostics"
        self.product.save(update_fields=["brand"])
        hematology = Category.objects.get(slug="hematology")
        hematology_product = Product.objects.create(
            category=hematology,
            name="Acme Hematology System",
            slug="acme-hematology-system-grouped",
            product_code="ACME-GROUPED-HEMA",
            brand="Acme Diagnostics",
            short_description="A grouped hematology product.",
            description="A grouped hematology product.",
        )

        response = self.client.get(
            reverse("product_list"),
            {"brand": "acme-diagnostics"},
        )
        grouped_products = [
            product
            for group in response.context["product_groups"]
            for product in group["products"]
        ]

        self.assertEqual(
            {product.pk for product in grouped_products},
            {self.product.pk, hematology_product.pk},
        )
        self.assertEqual(len(grouped_products), len({p.pk for p in grouped_products}))
        self.assertContains(response, 'class="catalog-category-groups"')
        self.assertContains(response, "Chemistry")
        self.assertContains(response, "Hematology")

    def test_specifications_are_parsed_into_unlimited_nested_lists(self):
        value = (
            'Interface connector:\n'
            '  Serial interface connector (two): daisy-chained RS 232\n'
            '    Port direction:\n'
            '      "In" port toward computer, "out" port away.\n'
            'Color: Two-tone gray'
        )
        nodes = parse_specifications(value)

        self.assertEqual([node.text for node in nodes], [
            "Interface connector:",
            "Color: Two-tone gray",
        ])
        self.assertEqual(
            nodes[0].children[0].text,
            "Serial interface connector (two): daisy-chained RS 232",
        )
        self.assertEqual(
            nodes[0].children[0].children[0].children[0].text,
            '"In" port toward computer, "out" port away.',
        )
        rendered = str(render_specification_list(nodes))
        self.assertEqual(rendered.count("<ul"), 4)
        self.assertIn("&quot;In&quot; port toward computer", rendered)

    def test_orphan_child_becomes_top_level_and_empty_lines_are_ignored(self):
        nodes = parse_specifications("\n\tOrphan specification\n\nTop level")
        self.assertEqual(
            [node.text for node in nodes],
            ["Orphan specification", "Top level"],
        )

    def test_specification_output_is_escaped_on_every_product_page(self):
        self.product.specifications = (
            'Safe parent <script>alert("x")</script>\n'
            '  Child & supporting value'
        )
        self.product.save(update_fields=["specifications"])

        response = self.client.get(self.product.get_absolute_url())
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(
            response,
            "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;",
        )
        self.assertContains(
            response,
            '<ul class="spec-list"><li>Safe parent',
        )
        self.assertContains(response, "<ul><li>Child &amp; supporting value</li></ul>")

    def test_search(self):
        response = self.client.get(reverse("product_list"), {"q": "Analyser"})
        self.assertContains(response, "Test Analyser")

    def test_search_reuses_name_brand_category_and_product_code_fields(self):
        self.product.brand = "Acme Diagnostics"
        self.product.save(update_fields=["brand"])

        for query in ("Analyser", "Acme", "Chemistry", "TEST-1"):
            with self.subTest(query=query):
                response = self.client.get(reverse("product_list"), {"q": query})
                self.assertContains(response, self.product.name)

    def test_brand_filter_is_dynamic_case_insensitive_and_combines_with_category(self):
        from core.models import Partner

        Partner.objects.create(name="Acme Diagnostics", is_active=True)
        self.product.brand = "ACME DIAGNOSTICS"
        self.product.save(update_fields=["brand"])
        other_chemistry = Product.objects.create(
            category=self.category,
            name="Other Chemistry Product",
            slug="other-chemistry-product",
            product_code="OTHER-CHEM",
            brand="Another Brand",
            short_description="Another product.",
            description="Another product.",
        )
        hematology = Category.objects.get(slug="hematology")
        acme_hematology = Product.objects.create(
            category=hematology,
            name="Acme Hematology Product",
            slug="acme-hematology-product",
            product_code="ACME-HEMA",
            brand="Acme Diagnostics",
            short_description="A hematology product.",
            description="A hematology product.",
        )

        response = self.client.get(reverse("product_list"), {
            "category": "chemistry",
            "brand": "acme-diagnostics",
        })
        product_names = list(response.context["products"].values_list(
            "name", flat=True
        ))

        self.assertEqual(product_names, [self.product.name])
        self.assertNotIn(other_chemistry.name, product_names)
        self.assertNotIn(acme_hematology.name, product_names)
        self.assertEqual(response.context["selected_brand_name"], "Acme Diagnostics")
        self.assertContains(response, "Brand: Acme Diagnostics")
        self.assertContains(response, ">Clear Filter</a>")
        self.assertContains(
            response,
            "/products/category/hematology/",
        )
        self.assertNotContains(
            response,
            "/products/category/hematology/?brand=acme-diagnostics",
        )
        self.assertContains(response, 'name="brand" value="acme-diagnostics"')
        self.assertContains(response, 'name="category" value="chemistry"')

    def test_brand_filtered_category_uses_landing_page_and_combined_filter(self):
        from core.models import Partner

        Partner.objects.create(name="Acme Diagnostics", is_active=True)
        self.product.brand = "ACME DIAGNOSTICS"
        self.product.save(update_fields=["brand"])
        unrelated = Product.objects.create(
            category=self.category,
            name="Unrelated Chemistry Product",
            slug="unrelated-chemistry-product",
            product_code="UNRELATED-CHEM",
            brand="Another Manufacturer",
            short_description="Another product.",
            description="Another product.",
        )

        response = self.client.get(self.category.get_absolute_url(), {
            "brand": "acme-diagnostics",
        })

        self.assertContains(response, "Laboratory discipline")
        self.assertNotContains(response, "Chemistry solutions")
        self.assertContains(response, "Showing <strong>Acme Diagnostics</strong> products")
        self.assertContains(response, self.product.name)
        self.assertNotContains(response, unrelated.name)
        self.assertEqual(list(response.context["products"]), [self.product])
        self.assertEqual(response.context["selected_brand_name"], "Acme Diagnostics")
        self.assertContains(response, "1 product")

    def test_brand_catalogue_category_links_replace_the_brand_context(self):
        from core.models import Partner

        Partner.objects.create(name="Acme Diagnostics", is_active=True)
        self.product.brand = "Acme Diagnostics"
        self.product.save(update_fields=["brand"])

        response = self.client.get(reverse("product_list"), {
            "brand": "acme-diagnostics",
        })

        for category in Category.objects.filter(slug__in=PUBLIC_CATEGORY_SLUGS):
            with self.subTest(category=category.slug):
                self.assertContains(
                    response,
                    f'href="{category.get_absolute_url()}"',
                )
                self.assertNotContains(
                    response,
                    f'{category.get_absolute_url()}?brand=acme-diagnostics',
                )

    def test_brand_links_replace_previous_category_brand_and_search_context(self):
        from core.models import Partner

        Partner.objects.create(name="Acme Diagnostics", is_active=True)
        Partner.objects.create(name="Another Manufacturer", is_active=True)
        self.product.brand = "Acme Diagnostics"
        self.product.save(update_fields=["brand"])
        Product.objects.create(
            category=self.category,
            name="Another Manufacturer Product",
            slug="another-manufacturer-product",
            product_code="ANOTHER-MFR-1",
            brand="Another Manufacturer",
            short_description="Another manufacturer product.",
            description="Another manufacturer product.",
        )

        response = self.client.get(reverse("product_list"), {
            "brand": "acme-diagnostics",
            "category": "chemistry",
            "q": "Analyser",
        })

        replacement_url = f'{reverse("product_list")}?brand=another-manufacturer'
        self.assertContains(response, f'href="{replacement_url}"')
        self.assertNotContains(
            response,
            "brand=another-manufacturer&amp;category=chemistry",
        )
        self.assertNotContains(
            response,
            "brand=another-manufacturer&amp;q=Analyser",
        )

    def test_brand_catalogue_breadcrumb_contains_only_active_manufacturer(self):
        from core.models import Partner

        Partner.objects.create(name="Vatech Dental", is_active=True)
        response = self.client.get(
            reverse("product_list"),
            {"brand": "vatech-dental"},
        )

        self.assertContains(
            response,
            '<a href="/">Home</a><span>/</span><a href="/products/">Products</a><span>/</span><strong>Dental Imaging</strong>',
            html=True,
        )

    def test_unfiltered_catalogue_category_links_open_canonical_landing_pages(self):
        response = self.client.get(reverse("product_list"))

        for slug in ("chemistry", "immunoassay", "hematology", "microbiology"):
            category = Category.objects.get(slug=slug)
            with self.subTest(category=slug):
                self.assertContains(
                    response,
                    f'href="{category.get_absolute_url()}"',
                )
                self.assertNotContains(
                    response,
                    f'href="{reverse("product_list")}?category={slug}"',
                )

    def test_standard_and_microbiology_canonical_category_destinations(self):
        for slug in ("chemistry", "immunoassay", "hematology"):
            category = Category.objects.get(slug=slug)
            with self.subTest(category=slug):
                response = self.client.get(category.get_absolute_url())
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "catalog/category_detail.html")
                self.assertEqual(response.context["category"], category)
                self.assertContains(response, category.description)
                self.assertNotContains(response, f"{category.name} solutions")
                self.assertNotContains(response, 'class="section category-intro"')

        microbiology = Category.objects.get(slug="microbiology")
        response = self.client.get(microbiology.get_absolute_url())
        self.assertEqual(
            microbiology.get_absolute_url(),
            reverse("microbiology_landing"),
        )
        self.assertTemplateUsed(response, "catalog/microbiology_landing.html")
        self.assertContains(response, "Full Line of Microbiology Products")

    def test_clearing_brand_stays_on_current_category_page(self):
        from core.models import Partner

        Partner.objects.create(name="Acme Diagnostics", is_active=True)
        self.product.brand = "Acme Diagnostics"
        self.product.save(update_fields=["brand"])

        response = self.client.get(self.category.get_absolute_url(), {
            "brand": "acme-diagnostics",
        })

        self.assertEqual(response.context["clear_brand_url"], self.category.get_absolute_url())
        self.assertContains(
            response,
            f'href="{self.category.get_absolute_url()}">View all Chemistry products</a>',
        )

    def test_empty_brand_category_combination_keeps_category_landing_page(self):
        from core.models import Partner

        Partner.objects.create(name="Future Laboratory Brand", is_active=True)

        response = self.client.get(self.category.get_absolute_url(), {
            "brand": "future-laboratory-brand",
        })

        self.assertEqual(list(response.context["products"]), [])
        self.assertNotContains(response, "Chemistry solutions")
        self.assertContains(
            response,
            "No products from Future Laboratory Brand are currently available in Chemistry.",
        )
        self.assertContains(response, "View all Chemistry products")
        self.assertContains(response, "View all Future Laboratory Brand products")

    def test_category_brand_matching_is_case_insensitive(self):
        from core.models import Partner

        Partner.objects.create(name="Acme Diagnostics", is_active=True)
        self.product.brand = "aCmE dIaGnOsTiCs"
        self.product.save(update_fields=["brand"])

        response = self.client.get(self.category.get_absolute_url(), {
            "brand": "ACME-DIAGNOSTICS",
        })

        self.assertEqual(list(response.context["products"]), [self.product])
        self.assertContains(response, self.product.name)

    def test_normal_category_page_remains_unfiltered(self):
        first = Product.objects.create(
            category=self.category,
            name="First Manufacturer Product",
            slug="first-manufacturer-product",
            product_code="FIRST-MFR",
            brand="First Manufacturer",
            short_description="First product.",
            description="First product.",
        )
        second = Product.objects.create(
            category=self.category,
            name="Second Manufacturer Product",
            slug="second-manufacturer-product",
            product_code="SECOND-MFR",
            brand="Second Manufacturer",
            short_description="Second product.",
            description="Second product.",
        )

        response = self.client.get(self.category.get_absolute_url())

        self.assertContains(response, self.product.name)
        self.assertContains(response, first.name)
        self.assertContains(response, second.name)
        self.assertEqual(response.context["selected_brand"], "")
        self.assertNotContains(response, "category-brand-context")

    def test_brand_and_search_filters_work_together(self):
        self.product.brand = "Acme Diagnostics"
        self.product.save(update_fields=["brand"])
        Product.objects.create(
            category=self.category,
            name="Unrelated Analyser",
            slug="unrelated-analyser",
            product_code="OTHER-1",
            brand="Another Brand",
            short_description="Reliable testing.",
            description="Another product.",
        )

        response = self.client.get(reverse("product_list"), {
            "q": "Analyser",
            "category": "chemistry",
            "brand": "acme-diagnostics",
        })

        self.assertEqual(
            list(response.context["products"].values_list("name", flat=True)),
            [self.product.name],
        )

    def test_partner_without_products_still_has_a_highlighted_brand_filter(self):
        from core.models import Partner

        Partner.objects.create(name="Future Laboratory Brand", is_active=True)

        response = self.client.get(reverse("product_list"), {
            "brand": "future-laboratory-brand",
        })

        self.assertEqual(list(response.context["products"]), [])
        self.assertEqual(
            response.context["selected_brand_name"],
            "Future Laboratory Brand",
        )
        self.assertContains(
            response,
            'class="active" href="/products/?brand=future-laboratory-brand"',
        )
        self.assertContains(response, "View All Products")

    def test_every_partner_brand_filter_excludes_other_manufacturers(self):
        from core.models import Partner
        from django.utils.text import slugify

        partners = (
            "Beckman Coulter",
            "DIAGNOSTICS i.n.c.",
            "Medical Electronic Systems",
            "SD Biosensor",
            "Bioer Technology",
            "Molbio Diagnostics",
            "Biosan",
            "Polycheck",
            "Turklab",
            "GeneProof",
        )
        products = []
        for index, partner_name in enumerate(partners):
            Partner.objects.create(name=partner_name, is_active=True)
            products.append(Product.objects.create(
                category=self.category,
                name=f"{partner_name} Product",
                slug=f"partner-product-{index}",
                product_code=f"PARTNER-{index}",
                brand=partner_name.upper() if index == 0 else partner_name,
                short_description="Partner product.",
                description="Partner product.",
            ))

        for partner_name, expected_product in zip(partners, products):
            brand_slug = slugify(partner_name)
            with self.subTest(partner=partner_name):
                response = self.client.get(reverse("product_list"), {
                    "brand": brand_slug,
                    "category": "chemistry",
                    "q": "Product",
                })
                result_names = list(
                    response.context["products"].values_list("name", flat=True)
                )
                self.assertEqual(result_names, [expected_product.name])
                self.assertContains(
                    response,
                    f"Brand: {catalogue_display_label(partner_name, partner_name)}",
                )
                self.assertContains(response, ">Clear Filter</a>")

    def test_laboratory_display_labels_match_across_menu_and_catalogue(self):
        expected_labels = {
            "polycheck": "Allergy and Autoimmune Tests",
            "molbio": "Truenat® Real-Time PCR",
            "medical-electronic-systems": "Semen Analyzers (SQA)",
            "ama-helic-ubt-reader": "Urea Breath Test",
            "sd-biosensor": "SD Biosensor Rapid Test",
            "eschweiler-abg": "Eschweiler ABG",
        }
        home = self.client.get(reverse("home"))
        catalogue = self.client.get(reverse("product_list"))

        for slug, label in expected_labels.items():
            with self.subTest(slug=slug):
                category = Category.objects.get(slug=slug)
                self.assertEqual(category.navigation_name, label)
                self.assertContains(home, f"<span>{label}</span>")
                self.assertContains(
                    catalogue,
                    f'href="{category.get_absolute_url()}">{label}</a>',
                )

    def test_category_subcategory_and_product_breadcrumbs_use_display_label(self):
        category = Category.objects.get(slug="ama-helic-ubt-reader")
        product = Product.objects.filter(category=category).first()
        self.assertIsNotNone(product)

        category_page = self.client.get(category.get_absolute_url())
        detail_page = self.client.get(product.get_absolute_url())

        self.assertContains(category_page, "<h1>Urea Breath Test</h1>")
        self.assertContains(
            detail_page,
            f'href="{category.get_absolute_url()}">Urea Breath Test</a>',
        )
        self.assertContains(
            detail_page,
            "<dt>Brand</dt><dd>Urea Breath Test</dd>",
        )

    def test_product_suggestions_require_two_characters(self):
        response = self.client.get(reverse("product_suggestions"), {"q": "T"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"results": []})

    def test_product_suggestions_use_shared_search_and_product_links(self):
        self.product.brand = "Acme Diagnostics"
        self.product.image = "products/search-thumbnail.png"
        self.product.save(update_fields=["brand", "image"])

        for query in ("Analyser", "Acme", "Chemistry", "TEST-1"):
            with self.subTest(query=query):
                response = self.client.get(
                    reverse("product_suggestions"),
                    {"q": query},
                )
                result = next(
                    item for item in response.json()["results"]
                    if item["name"] == self.product.name
                )
                self.assertEqual(result["url"], self.product.get_absolute_url())
                self.assertEqual(result["brand"], "Acme Diagnostics")
                self.assertIn("search-thumbnail.png", result["thumbnail"])

    def test_laboratory_navigation_is_the_requested_flat_list(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Browse by equipment group")
        content = response.content.decode()
        start = content.index('id="laboratory-menu-heading"')
        end = content.index('id="medical-equipment-menu-heading"', start)
        laboratory = content[start:end]
        labels = (
            "Chemistry",
            "Immunoassay",
            "Hematology",
            "Urinalysis",
            "Microbiology",
            "Blood Banking",
            "Allergy and Autoimmune Tests",
            "Truenat® Real-Time PCR",
            "Semen Analyzers (SQA)",
            "Urea Breath Test",
            "SD Biosensor Rapid Test",
            "Eschweiler ABG",
        )
        positions = [laboratory.index(f"<span>{label}</span>") for label in labels]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("Beckman Coulter", laboratory)
        self.assertEqual(laboratory.count("manufacturer-menu-toggle"), 6)

    def test_flat_laboratory_items_restore_only_existing_child_menus(self):
        from catalog.navigation import product_navigation_groups

        laboratory = next(
            group for group in product_navigation_groups()
            if group["slug"] == "laboratory"
        )
        items = {item["label"]: item for item in laboratory["flat_items"]}
        self.assertEqual(
            [child["label"] for child in items[
                "Allergy and Autoimmune Tests"
            ]["children"]],
            ["Autoimmune", "Allergy", "Veterinary"],
        )
        self.assertEqual(
            [child["label"] for child in items[
                "Truenat® Real-Time PCR"
            ]["children"]],
            [
                "Truenat", "Truenat Assays", "iBreastExam",
                "ProRad Atlas", "OptraScan",
            ],
        )
        self.assertEqual(
            [child["label"] for child in items["Urea Breath Test"]["children"]],
            ["HELIC® ABT Reader"],
        )
        self.assertEqual(
            [child["label"] for child in items["Eschweiler ABG"]["children"]],
            ["Modular Pro", "Combi Line 2"],
        )
        self.assertEqual(
            [child["label"] for child in items[
                "Semen Analyzers (SQA)"
            ]["children"]],
            [
                "Automated Semen Analysis Solutions",
                "MaleMan Reference Lab Services",
                "Consumer Semen Analysis Solutions",
                "Semen Analysis & Validation Kits",
                "Veterinary Semen Analysis Solutions",
            ],
        )
        self.assertEqual(
            [child["label"] for child in items[
                "SD Biosensor Rapid Test"
            ]["children"]],
            ["STANDARD Q"],
        )
        self.assertNotIn("Beckman Coulter", items)

    def test_product_menu_uses_requested_three_category_groups(self):
        response = self.client.get(reverse("home"))
        content = response.content.decode()
        menu_start = content.index('<div class="discipline-menu">')
        menu_end = content.index('</aside>', menu_start)
        menu = content[menu_start:menu_end]
        self.assertNotIn('role="tab"', menu)
        self.assertNotIn('equipment-panel', menu)
        self.assertNotIn('<small>View all ', menu)
        for group_slug in ("laboratory", "medical", "dental"):
            self.assertIn(
                f'href="{reverse("equipment_group_products", args=[group_slug])}"',
                menu,
            )

        headings = (
            'id="laboratory-menu-heading"',
            'id="medical-equipment-menu-heading"',
            'id="dental-equipment-menu-heading"',
        )
        heading_positions = [menu.index(heading) for heading in headings]
        self.assertEqual(heading_positions, sorted(heading_positions))

        laboratory_group = menu[heading_positions[0]:heading_positions[1]]
        medical_group = menu[heading_positions[1]:heading_positions[2]]
        dental_group_end = menu.index("</section>", heading_positions[2])
        dental_group = menu[heading_positions[2]:dental_group_end]

        for category_name in (
            "Chemistry",
            "Immunoassay",
            "Hematology",
            "Urinalysis",
            "Microbiology",
            "Blood Banking",
            "Allergy and Autoimmune Tests",
            "Truenat® Real-Time PCR",
            "Semen Analyzers (SQA)",
            "Urea Breath Test",
            "SD Biosensor Rapid Test",
            "Eschweiler ABG",
        ):
            self.assertIn(category_name, laboratory_group)
        self.assertNotIn("Beckman Coulter", laboratory_group)
        self.assertEqual(laboratory_group.count("manufacturer-menu-toggle"), 6)
        self.assertNotIn("ZEISS Light Microscope", laboratory_group)
        self.assertNotIn("ZEISS Microscopy", medical_group)
        self.assertIn("ZEISS Light Microscope", medical_group)
        self.assertIn("Dental Imaging", dental_group)
        self.assertNotIn("Vatech Dental", dental_group)
        for slug, label in (
            ("3d-imaging", "3D Imaging"),
            ("2d-imaging", "2D Imaging"),
            ("ios-iox", "IOS and IOX"),
        ):
            self.assertIn(label, dental_group)
            self.assertIn(
                f'href="{reverse("vatech_category", args=[slug])}"',
                dental_group,
            )

        for slug in (
            "chemistry", "immunoassay", "hematology", "urinalysis",
            "microbiology", "blood-banking",
        ):
            category = Category.objects.get(slug=slug)
            self.assertIn(
                f'href="{category.get_absolute_url()}"',
                laboratory_group,
            )
        mes_category = Category.objects.get(slug="medical-electronic-systems")
        mes_subcategory = mes_category.subcategories.get(
            slug="automated-semen-analysis-solutions"
        )
        self.assertIn(
            f'href="{mes_subcategory.get_absolute_url()}"',
            laboratory_group,
        )
        self.assertIn(
            f'href="{Category.objects.get(slug="sd-biosensor").subcategories.get(slug="standard-q").get_absolute_url()}"',
            laboratory_group,
        )
        vatech = Category.objects.get(slug="vatech-dental")
        for subcategory in vatech.subcategories.all():
            self.assertIn(
                f'href="{subcategory.get_absolute_url()}"',
                dental_group,
            )
        light_microscopes = Category.objects.get(slug="light-microscopes")
        self.assertIn(
            f'href="{light_microscopes.get_absolute_url()}"',
            medical_group,
        )

    def test_equipment_group_pages_use_live_hierarchy_without_duplicates(self):
        from catalog.navigation import equipment_group_category_ids

        memberships = equipment_group_category_ids()
        for group_slug, group_name in (
            ("laboratory", "Laboratory"),
            ("medical", "Medical Equipment"),
            ("dental", "Dental Equipment"),
        ):
            with self.subTest(group=group_slug):
                response = self.client.get(reverse(
                    "equipment_group_products",
                    args=[group_slug],
                ))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f"<h1>{group_name}</h1>", html=True)
                self.assertNotContains(response, "unique product")
                response_html = response.content.decode()
                sidebar_start = response_html.index(
                    '<aside class="category-sidebar">'
                )
                sidebar_end = response_html.index("</aside>", sidebar_start)
                self.assertNotIn(
                    "<span>",
                    response_html[sidebar_start:sidebar_end],
                )
                expected_ids = list(
                    Product.objects.filter(
                        is_active=True,
                        is_catalogue_listing=True,
                        category__is_active=True,
                        category_id__in=memberships[group_slug],
                    )
                    .order_by("name", "pk")
                    .values_list("pk", flat=True)
                    .distinct()
                )
                rendered_ids = [product.pk for product in response.context["products"]]
                self.assertEqual(set(rendered_ids), set(expected_ids))
                self.assertEqual(len(rendered_ids), len(expected_ids))
                self.assertEqual(len(rendered_ids), len(set(rendered_ids)))

                next_response = self.client.get(reverse(
                    "equipment_group_products",
                    args=[group_slug],
                ))
                next_ids = [
                    product.pk
                    for product in next_response.context["products"]
                ]
                self.assertEqual(set(next_ids), set(expected_ids))
                self.assertEqual(len(next_ids), len(set(next_ids)))
                if len(expected_ids) > 1:
                    self.assertNotEqual(next_ids[0], rendered_ids[0])

        dental = self.client.get(reverse(
            "equipment_group_products",
            args=["dental"],
        ))
        vatech = Category.objects.get(slug="vatech-dental")
        self.assertContains(dental, "Dental Imaging")
        self.assertContains(dental, f'href="{vatech.get_absolute_url()}"')

    def test_unknown_equipment_group_is_not_found(self):
        response = self.client.get(reverse(
            "equipment_group_products",
            args=["unknown"],
        ))
        self.assertEqual(response.status_code, 404)

    def test_vatech_category_pages_show_only_their_products(self):
        expected = {
            "3d-imaging": 9,
            "2d-imaging": 3,
            "ios-iox": 6,
        }
        for slug, count in expected.items():
            with self.subTest(slug=slug):
                response = self.client.get(
                    reverse("vatech_category", args=[slug])
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'class="category-detail-hero subcategory-detail-hero vatech-category-hero"')
                self.assertContains(response, 'class="category-hero-image subcategory-hero-image"')
                self.assertEqual(len(response.context["products"]), count)
                self.assertTrue(all(
                    product.subcategory.slug == slug
                    and product.category.slug == "vatech-dental"
                    and product.brand == "Vatech Dental"
                    for product in response.context["products"]
                ))

    def test_vatech_products_use_existing_catalogue_and_detail_architecture(self):
        vatech_products = Product.objects.filter(
            category__slug="vatech-dental",
            brand="Vatech Dental",
        )
        self.assertEqual(vatech_products.count(), 18)
        catalogue = self.client.get(reverse("product_list"), {"brand": "vatech-dental"})
        self.assertEqual(catalogue.status_code, 200)
        self.assertEqual(list(catalogue.context["products"]), list(vatech_products.order_by("name")))
        item = vatech_products.get(name="Vatech A9")
        detail = self.client.get(item.get_absolute_url())
        self.assertEqual(detail.status_code, 200)
        self.assertTemplateUsed(detail, "catalog/product_detail.html")
        self.assertContains(detail, "Vatech A9")
        self.assertContains(detail, "Available on request")
        self.assertContains(detail, "Request price")

    def test_vatech_import_is_idempotent(self):
        call_command("import_vatech_dental_products", skip_images=True, verbosity=0)
        call_command("import_vatech_dental_products", skip_images=True, verbosity=0)
        self.assertEqual(
            Product.objects.filter(
                category__slug="vatech-dental",
                brand="Vatech Dental",
            ).count(),
            18,
        )

    def test_laboratory_menu_remains_limited_to_the_configured_flat_list(self):
        from core.models import Partner

        future_brand = Partner.objects.create(
            name="Future Diagnostics",
            equipment_group="laboratory",
            menu_order=50,
            is_active=True,
        )
        future_brand.menu_categories.add(self.category)
        product = Product.objects.create(
            category=self.category,
            name="Future Diagnostic System",
            slug="future-diagnostic-system",
            product_code="FUTURE-NAV-1",
            brand="Future Diagnostics",
            short_description="Future system.",
            description="Future system.",
        )

        response = self.client.get(reverse("home"))
        content = response.content.decode()
        menu_start = content.index('<div class="discipline-menu">')
        menu_end = content.index("</aside>", menu_start)
        menu = content[menu_start:menu_end]

        self.assertNotIn("Future Diagnostics", menu)
        self.assertNotIn(product.get_absolute_url(), menu)
        self.assertIn("Allergy and Autoimmune Tests", menu)

    def test_product_menu_stops_at_category_links(self):
        response = self.client.get(reverse("home"))
        content = response.content.decode()
        menu_start = content.index('<div class="discipline-menu">')
        menu_end = content.index("</aside>", menu_start)
        menu = content[menu_start:menu_end]

        self.assertNotIn("category-products-toggle", menu)
        self.assertNotIn("manufacturer-products", menu)
        self.assertNotIn("Show Chemistry products", menu)
        for category in Category.objects.filter(slug__in=(
            "chemistry", "immunoassay", "hematology", "urinalysis",
            "microbiology", "blood-banking",
        )):
            self.assertIn(
                f'class="manufacturer-row manufacturer-direct-link" href="{category.get_absolute_url()}"',
                menu,
            )

    def test_only_approved_categories_have_public_landing_pages(self):
        self.assertEqual(
            list(
                Category.objects.filter(is_active=True)
                .order_by("display_order")
                .values_list("slug", flat=True)
            ),
            list(PUBLIC_CATEGORY_SLUGS),
        )
        for slug in PUBLIC_CATEGORY_SLUGS:
            response = self.client.get(reverse("category_detail", args=[slug]))
            if slug == "microbiology":
                self.assertRedirects(response, reverse("microbiology_landing"))
            else:
                self.assertEqual(response.status_code, 200)

    def test_removed_category_products_are_excluded_everywhere_public(self):
        removed_category = Category.objects.create(
            name="Molecular Biology",
            slug="molecular-biology-extra",
            is_active=True,
        )
        removed_product = Product.objects.create(
            category=removed_category,
            name="Hidden PCR System",
            slug="hidden-pcr-system",
            product_code="HIDDEN-PCR",
            short_description="Must not be public.",
            description="Must not be public.",
            is_active=True,
            is_featured=True,
        )

        catalogue = self.client.get(reverse("product_list"), {"q": "Hidden PCR"})
        homepage = self.client.get(reverse("home"))
        self.assertNotContains(catalogue, removed_product.name)
        self.assertNotContains(homepage, removed_category.name)
        self.assertNotContains(homepage, removed_product.name)
        self.assertEqual(
            self.client.get(removed_category.get_absolute_url()).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(removed_product.get_absolute_url()).status_code,
            404,
        )

    def test_light_microscope_category_contains_zeiss_families(self):
        category = Category.objects.get(slug="light-microscopes")
        self.assertEqual(category.name, "ZEISS Light Microscopes")
        self.assertEqual(
            list(category.subcategories.values_list("name", flat=True)),
            [
                "Widefield Microscopes",
                "Stereo & Zoom Microscopes",
                "Digital Microscopes",
                "Super-Resolution Microscopes",
                "Light Sheet Microscopes",
                "Confocal Laser Scanning Microscopes",
            ],
        )
        self.assertEqual(category.products.filter(brand="ZEISS").count(), 36)
        self.assertTrue(
            {
                "ZEISS Stemi 355",
                "ZEISS SteREO Discovery.V8",
                "ZEISS SteREO Discovery.V12",
                "ZEISS SteREO Discovery.V20",
                "ZEISS Smartzoom 100",
                "ZEISS Lattice SIM 3",
                "ZEISS Lightsheet 7",
                "ZEISS LSM 990",
                "ZEISS Axiovert for Materials",
            }.issubset(
                set(category.products.values_list("name", flat=True))
            )
        )
        self.assertEqual(
            category.products.filter(subcategory__isnull=True).count(),
            0,
        )
        self.assertEqual(
            set(category.products.values_list("availability", flat=True)),
            {
                "on_request",
            },
        )

        response = self.client.get(category.get_absolute_url(), {"brand": "zeiss"})
        self.assertContains(
            response,
            'class="category-hero-image zeiss-light-microscopes-image-fit"',
        )
        self.assertContains(response, "ZEISS Light Microscope subcategories")
        self.assertContains(response, "Widefield Microscopes")
        self.assertContains(response, "Confocal Laser Scanning Microscopes")
        self.assertContains(response, "ZEISS LSM 990")
        product = category.products.get(product_code="ZEISS-LM-CF-002")
        detail = self.client.get(product.get_absolute_url())
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Request price")
        self.assertContains(detail, "Available on request")

        subcategory = category.subcategories.get(slug="widefield-microscopes")
        subcategory_page = self.client.get(subcategory.get_absolute_url())
        self.assertContains(
            subcategory_page,
            "category-hero-image subcategory-hero-image "
            "zeiss-light-microscopes-cutout-fit",
        )

    def test_zeiss_medical_navigation_only_exposes_light_microscopes(self):
        response = self.client.get(reverse("home"))
        content = response.content.decode()
        start = content.index(
            'id="medical-equipment-menu-heading"'
        )
        end = content.index("</section>", start)
        medical = content[start:end]
        category = Category.objects.get(slug="light-microscopes")

        self.assertNotIn("ZEISS Microscopy", medical)
        self.assertIn(
            '<span>ZEISS Light Microscopes</span><b>→</b>',
            medical,
        )
        self.assertIn(
            f'href="{category.get_absolute_url()}"',
            medical,
        )
        self.assertNotIn(f'href="{reverse("zeiss_microscopy")}"', medical)
        self.assertNotIn(
            'href="/products/?brand=zeiss"',
            medical,
        )
        self.assertNotIn("manufacturer-menu-toggle", medical)

        microscopy_page = self.client.get(reverse("zeiss_microscopy"))
        self.assertEqual(microscopy_page.status_code, 200)
        self.assertContains(microscopy_page, "Products coming soon")
        self.assertContains(
            microscopy_page,
            category.get_absolute_url(),
        )
        self.assertNotContains(microscopy_page, 'class="product-card"')

    def test_all_zeiss_products_belong_to_light_microscopes_only(self):
        category = Category.objects.get(slug="light-microscopes")
        products = Product.objects.filter(brand__iexact="ZEISS")

        self.assertEqual(products.count(), 36)
        self.assertFalse(products.exclude(category=category).exists())
        self.assertFalse(products.filter(subcategory__isnull=True).exists())

        partners = self.client.get(reverse("partners"))
        self.assertContains(partners, 'id="partner-zeiss"')
        self.assertNotContains(partners, reverse("zeiss_microscopy"))
        self.assertNotContains(partners, '/products/?brand=zeiss')

    def test_category_page_lists_products_linking_to_own_pages(self):
        response = self.client.get(self.category.get_absolute_url())
        self.assertNotContains(response, "Chemistry solutions")
        self.assertContains(response, "Test Analyser")
        self.assertContains(response, self.product.get_absolute_url())

    def test_category_page_omits_repeated_overview_block(self):
        response = self.client.get(self.category.get_absolute_url())

        self.assertContains(response, self.category.description)
        self.assertNotContains(response, 'class="section category-intro"')
        self.assertNotContains(response, "Open any product below")

    def test_blood_banking_category_uses_scoped_contain_image(self):
        blood_banking = Category.objects.get(slug="blood-banking")

        response = self.client.get(blood_banking.get_absolute_url())
        chemistry = self.client.get(self.category.get_absolute_url())

        self.assertContains(
            response,
            'class="category-hero-image blood-banking-image-fit"',
        )
        self.assertNotContains(chemistry, "blood-banking-image-fit")

    def test_pk7400_uses_scoped_card_and_detail_image_fit(self):
        blood_banking = Category.objects.get(slug="blood-banking")
        product = Product.objects.create(
            category=blood_banking,
            name="PK7400 Automated Microplate System",
            slug="pk7400-image-fit-test",
            product_code="SL-CC-203",
            short_description="Blood banking automation.",
            description="Blood banking automation.",
            image="products/pk7400-test.webp",
            source_image="products/originals/pk7400-test.webp",
        )

        category = self.client.get(product.category.get_absolute_url())
        detail = self.client.get(product.get_absolute_url())
        chemistry = self.client.get(self.category.get_absolute_url())

        self.assertContains(category, "pk7400-card-image-fit", count=1)
        self.assertContains(detail, "pk7400-detail-image-fit", count=1)
        self.assertNotContains(chemistry, "pk7400-card-image-fit")
        self.assertNotContains(chemistry, "pk7400-detail-image-fit")

    def test_microbiology_uses_custom_solution_landing_only(self):
        products = self.create_microbiology_products()
        category = Category.objects.get(slug="microbiology")
        category.image = "categories/current-informatics-image.webp"
        category.save(update_fields=["image"])

        self.assertEqual(
            category.get_absolute_url(),
            reverse("microbiology_landing"),
        )
        response = self.client.get(category.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalog/microbiology_landing.html")
        self.assertContains(response, "css/microbiology")
        self.assertContains(response, "Full Line of Microbiology Products")
        self.assertContains(response, "MicroScan ID/AST Panels")
        self.assertContains(response, "Microbiology Systems")
        self.assertContains(response, "Informatics")
        self.assertContains(response, "Microbiology Automation")
        self.assertContains(response, 'class="microbiology-solution-card"', count=4)
        self.assertNotContains(response, "5 products")
        self.assertNotContains(response, "4 products")
        self.assertNotContains(response, "Catalogue update")
        self.assertNotContains(response, "View solutions")
        self.assertNotContains(response, "Ask our team")
        self.assertNotContains(response, "Overview")
        self.assertNotContains(response, "microbiology-landing-hero")
        self.assertNotContains(response, 'class="product-grid category-product-grid"')
        self.assertEqual(len(response.context["solution_groups"]), 4)
        rendered_cards = response.content.decode().split(
            '<article class="microbiology-solution-card">'
        )[1:]
        self.assertIn(
            "/media/categories/current-informatics-image.webp",
            rendered_cards[0],
        )
        self.assertRegex(
            rendered_cards[1],
            r"/static/images/microbiology/microbiology-systems(?:\.[a-f0-9]{12})?\.jpg",
        )
        self.assertRegex(
            rendered_cards[2],
            r"/static/images/microbiology/informatics-labpro(?:\.[a-f0-9]{12})?\.jpg",
        )
        self.assertNotIn(
            "/media/categories/current-informatics-image.webp",
            rendered_cards[2],
        )
        self.assertRegex(
            rendered_cards[3],
            r"/static/images/microbiology/microbiology-automation(?:\.[a-f0-9]{12})?\.jpg",
        )
        for product in products:
            with self.subTest(product=product.product_code):
                if product.product_code not in {"SL-CC-228", "SL-CC-229"}:
                    self.assertContains(
                        response,
                        f'<a href="{product.get_absolute_url()}">{product.name}</a>',
                    )

        catalogue = self.client.get(reverse("product_list"))
        self.assertContains(
            catalogue,
            f'href="{reverse("microbiology_landing")}"',
        )

    def test_microbiology_cards_use_stable_product_code_order(self):
        self.create_microbiology_products()
        response = self.client.get(reverse("microbiology_landing"))
        groups = {
            group["slug"]: group
            for group in response.context["solution_groups"]
        }

        self.assertEqual(
            [
                product.product_code
                for product in groups["microscan-id-ast-panels"]["products"]
            ],
            [
                "SL-CC-217",
                "SL-CC-218",
                "SL-CC-219",
                "SL-CC-220",
                "SL-CC-221",
            ],
        )
        self.assertEqual(
            [
                product.product_code
                for product in groups["microbiology-systems"]["products"]
            ],
            ["SL-CC-222", "SL-CC-223", "SL-CC-224", "SL-CC-225"],
        )
        self.assertEqual(
            [
                product.product_code
                for product in groups["informatics"]["products"]
            ],
            ["SL-CC-226", "SL-CC-227"],
        )
        self.assertEqual(
            [
                product.product_code
                for product in groups["microbiology-automation"]["products"]
            ],
            ["SL-CC-228", "SL-CC-229"],
        )

    def test_microbiology_product_link_opens_existing_detail_page(self):
        self.create_microbiology_products()
        product = Product.objects.get(product_code="SL-CC-217")

        landing = self.client.get(reverse("microbiology_landing"))
        detail = self.client.get(product.get_absolute_url())

        self.assertContains(
            landing,
            f'<a href="{product.get_absolute_url()}">MicroScan Conventional Panels',
        )
        self.assertEqual(detail.status_code, 200)
        self.assertTemplateUsed(detail, "catalog/product_detail.html")
        self.assertContains(detail, "MicroScan Conventional Panels")
        self.assertContains(detail, "Request price")

    def test_microbiology_brand_filter_is_preserved_on_direct_product_links(self):
        from core.models import Partner

        Partner.objects.create(name="Beckman Coulter", is_active=True)
        self.create_microbiology_products()
        landing = self.client.get(reverse("microbiology_landing"), {
            "brand": "beckman-coulter",
        })

        self.assertContains(landing, "Showing <strong>Beckman Coulter</strong> solutions")
        self.assertContains(landing, "MicroScan Conventional Panels")
        self.assertContains(
            landing,
            f'href="{Product.objects.get(product_code="SL-CC-217").get_absolute_url()}"',
        )
        self.assertNotContains(landing, "/products/microbiology/microbiology-systems/")

    def test_informatics_links_and_automation_items_stay_on_landing_page(self):
        self.create_microbiology_products()
        response = self.client.get(reverse("microbiology_landing"))
        groups = {
            group["slug"]: group
            for group in response.context["solution_groups"]
        }

        self.assertEqual(
            [product.product_code for product in groups["informatics"]["products"]],
            ["SL-CC-226", "SL-CC-227"],
        )
        self.assertEqual(
            [
                product.product_code
                for product in groups["microbiology-automation"]["products"]
            ],
            ["SL-CC-228", "SL-CC-229"],
        )
        self.assertNotContains(response, "Catalogue update")
        self.assertNotContains(
            response,
            "Products for this solution area are available through our team.",
        )
        for code, name, _slug in self.NEW_MICROBIOLOGY_PRODUCTS[:2]:
            product = Product.objects.get(product_code=code)
            self.assertContains(
                response,
                f'<a href="{product.get_absolute_url()}">{name}</a>',
            )
        automation_card = response.content.decode().split(
            '<article class="microbiology-solution-card">'
        )[4]
        self.assertIn(
            '<button class="microbiology-solution-card__static-item" type="button">'
            'Copan WASP® DT: Walk-Away Specimen Processor</button>',
            automation_card,
        )
        self.assertIn(
            '<button class="microbiology-solution-card__static-item" type="button">'
            'Copan WASPLab™ System - Now featuring the Copan Colibri</button>',
            automation_card,
        )
        for code in ("SL-CC-228", "SL-CC-229"):
            self.assertNotIn(
                Product.objects.get(product_code=code).get_absolute_url(),
                automation_card,
            )

    def test_removed_microbiology_group_routes_return_not_found(self):
        self.assertEqual(
            self.client.get(
                "/products/microbiology/microscan-id-ast-panels/"
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                "/products/microbiology/microbiology-systems/"
            ).status_code,
            404,
        )

    def test_legacy_microbiology_category_url_preserves_query_parameters(self):
        response = self.client.get(
            reverse("category_detail", args=["microbiology"]),
            {"brand": "beckman-coulter"},
        )

        self.assertRedirects(
            response,
            f"{reverse('microbiology_landing')}?brand=beckman-coulter",
        )
