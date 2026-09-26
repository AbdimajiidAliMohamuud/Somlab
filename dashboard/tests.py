import base64

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import InMemoryStorage
from django.test import Client, TestCase
from django.test import override_settings
from django.urls import reverse
from botocore.exceptions import EndpointConnectionError

from catalog.models import (
    Category, Product, ProductMedia, ProductSubcategory, ProductVariant,
)
from core.models import Customer, CustomerProject, CustomerProjectMedia, Partner, Service


class UnavailableStorage(InMemoryStorage):
    def _save(self, name, content):
        raise EndpointConnectionError(endpoint_url="https://unavailable.invalid")

    def delete(self, name):
        raise EndpointConnectionError(endpoint_url="https://unavailable.invalid")


class CustomDashboardManagementTests(TestCase):
    def setUp(self):
        cache.clear()
        self.staff = User.objects.create_user(
            "manager", email="manager@somlab.so",
            password="test-pass-123", is_staff=True
        )
        self.client.force_login(self.staff)
        self.category = Category.objects.get(slug="chemistry")

    def test_admin_login_redirects_authorized_admin_to_dashboard(self):
        self.assertRedirects(
            self.client.get(reverse("admin_login")),
            reverse("dashboard"),
        )
        self.client.logout()
        self.assertEqual(self.client.get(reverse("admin_login")).status_code, 200)
        response = self.client.post(reverse("admin_login"), {
            "username": "manager",
            "password": "test-pass-123",
        })
        self.assertRedirects(response, reverse("dashboard"))

    def test_admin_can_login_with_email_and_remember_session(self):
        self.client.logout()
        response = self.client.post(reverse("admin_login"), {
            "username": "manager@somlab.so",
            "password": "test-pass-123",
            "remember_me": "on",
        })
        self.assertRedirects(response, reverse("dashboard"))
        self.assertFalse(self.client.session.get_expire_at_browser_close())
        self.assertGreater(self.client.session.get_expiry_age(), 60 * 60 * 24 * 29)

    def test_admin_login_without_remember_me_expires_with_browser(self):
        self.client.logout()
        response = self.client.post(reverse("admin_login"), {
            "username": "manager",
            "password": "test-pass-123",
        })
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_admin_logout_completely_ends_session(self):
        response = self.client.post(reverse("admin_logout"))
        self.assertRedirects(response, reverse("admin_login"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertRedirects(
            self.client.get(reverse("dashboard")),
            reverse("admin_login"),
        )

    def test_admin_login_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(reverse("admin_login"), {
            "username": "manager",
            "password": "test-pass-123",
        })
        self.assertEqual(response.status_code, 403)

    def test_admin_login_is_rate_limited(self):
        self.client.logout()
        for _ in range(5):
            response = self.client.post(reverse("admin_login"), {
                "username": "manager",
                "password": "incorrect-password",
            })
            self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("admin_login"), {
            "username": "manager",
            "password": "incorrect-password",
        })
        self.assertEqual(response.status_code, 429)
        self.assertContains(
            response,
            "Too many sign-in attempts",
            status_code=429,
        )

    def test_admin_password_is_securely_hashed(self):
        self.assertNotEqual(self.staff.password, "test-pass-123")
        self.assertTrue(self.staff.check_password("test-pass-123"))

    def test_product_can_be_created_and_edited_in_custom_dashboard(self):
        response = self.client.post(reverse("dashboard_product_add"), {
            "category": self.category.pk,
            "name": "Compact Analyser",
            "slug": "",
            "brand": "Somlab",
            "product_code": "SL-NEW-1",
            "short_description": "Compact routine analyser.",
            "description": "A dependable analyser for routine use.",
            "specifications": "Compact design",
            "availability": "on_request",
            "is_active": "on",
        })
        self.assertRedirects(response, reverse("dashboard_products"))
        product = Product.objects.get(product_code="SL-NEW-1")
        self.assertEqual(product.slug, "compact-analyser")
        self.assertEqual(product.availability, "on_request")

        response = self.client.post(reverse("dashboard_product_edit", args=[product.pk]), {
            "category": self.category.pk,
            "name": "Compact Analyser Plus",
            "slug": product.slug,
            "brand": "Somlab",
            "product_code": product.product_code,
            "short_description": product.short_description,
            "description": product.description,
            "specifications": product.specifications,
            "availability": "on_request",
            "is_active": "on",
        })
        self.assertRedirects(response, reverse("dashboard_products"))
        product.refresh_from_db()
        self.assertEqual(product.name, "Compact Analyser Plus")

    def test_new_product_form_defaults_to_available_on_request(self):
        response = self.client.get(reverse("dashboard_product_add"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["form"].fields["availability"].initial,
            "on_request",
        )

    def test_verified_microbiology_product_is_fully_editable_in_dashboard(self):
        product = Product.objects.get(product_code="SL-CC-227")
        edit_url = reverse("dashboard_product_edit", args=[product.pk])
        edit_page = self.client.get(edit_url)

        self.assertEqual(edit_page.status_code, 200)
        self.assertContains(edit_page, "LabPro Connect")
        self.assertContains(edit_page, "B1018-600")
        self.assertContains(edit_page, "B1018-601")
        self.assertContains(edit_page, "Gallery images")
        self.assertContains(edit_page, "Gallery videos")

        response = self.client.post(edit_url, {
            "category": product.category_id,
            "name": product.name,
            "slug": product.slug,
            "brand": product.brand,
            "product_code": product.product_code,
            "short_description": product.short_description,
            "description": product.description,
            "specifications": product.specifications,
            "availability": "on_request",
            "is_active": "on",
            "variants": (
                "LabPro Connect Open System | B1018-600\n"
                "LabPro Connect Closed System | B1018-601"
            ),
        })
        self.assertRedirects(response, reverse("dashboard_products"))
        product.refresh_from_db()
        self.assertEqual(product.availability, "on_request")
        self.assertEqual(
            list(product.variants.values_list("name", "model_number")),
            [
                ("LabPro Connect Open System", "B1018-600"),
                ("LabPro Connect Closed System", "B1018-601"),
            ],
        )

    @override_settings(STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.memory.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    })
    def test_product_form_accepts_multiple_gallery_files_and_variants(self):
        tiny_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
            "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        response = self.client.post(reverse("dashboard_product_add"), {
            "category": self.category.pk,
            "name": "Gallery Analyser",
            "slug": "",
            "brand": "Somlab",
            "product_code": "SL-GALLERY-1",
            "short_description": "An analyser with gallery media.",
            "description": "Gallery product description.",
            "specifications": "",
            "availability": "on_request",
            "is_active": "on",
            "variants": "Compact | GA-100\nAdvanced | GA-200",
            "gallery_images": [
                SimpleUploadedFile(
                    "front.jpg",
                    tiny_png,
                    content_type="image/png",
                ),
                SimpleUploadedFile(
                    "side.png",
                    tiny_png,
                    content_type="image/png",
                ),
            ],
            "gallery_videos": [
                SimpleUploadedFile(
                    "demo.mp4",
                    b"product video",
                    content_type="video/mp4",
                ),
            ],
        })
        self.assertRedirects(response, reverse("dashboard_products"))

        product = Product.objects.get(product_code="SL-GALLERY-1")
        self.assertEqual(product.gallery_media.filter(media_type="image").count(), 2)
        self.assertEqual(product.gallery_media.filter(media_type="video").count(), 1)
        self.assertEqual(
            list(product.variants.values_list("name", "model_number")),
            [("Compact", "GA-100"), ("Advanced", "GA-200")],
        )

        edit_page = self.client.get(
            reverse("dashboard_product_edit", args=[product.pk])
        )
        self.assertContains(edit_page, "Remove existing gallery media")
        self.assertContains(edit_page, "Compact | GA-100")

    def test_category_partner_and_service_management_pages(self):
        for name in (
            "dashboard_categories", "dashboard_subcategories",
            "dashboard_partners", "dashboard_customers", "dashboard_services",
        ):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)

        response = self.client.post(reverse("dashboard_subcategory_add"), {
            "category": self.category.pk,
            "name": "Special Chemistry Systems",
            "slug": "",
            "description": "Specialized chemistry platforms.",
            "display_order": 12,
            "is_active": "on",
        })
        self.assertRedirects(response, reverse("dashboard_subcategories"))
        self.assertTrue(ProductSubcategory.objects.filter(
            category=self.category,
            slug="special-chemistry-systems",
        ).exists())

        self.client.post(reverse("dashboard_partner_add"), {
            "name": "Example Diagnostics", "country": "Kenya",
            "description": "", "website": "", "display_order": 1, "is_active": "on",
        })
        self.assertTrue(Partner.objects.filter(name="Example Diagnostics").exists())

        self.client.post(reverse("dashboard_service_add"), {
            "name": "Calibration", "slug": "",
            "short_description": "Instrument calibration support.",
            "description": "Calibration and verification services.",
            "display_order": 1, "is_active": "on",
        })
        self.assertTrue(Service.objects.filter(slug="calibration").exists())

    @override_settings(STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.memory.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    })
    def test_subcategory_image_upload_preview_replace_and_remove(self):
        tiny_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
            "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        vatech = Category.objects.get(slug="vatech-dental")
        subcategory = ProductSubcategory.objects.get(
            category=vatech,
            slug="3d-imaging",
        )
        edit_url = reverse("dashboard_subcategory_edit", args=[subcategory.pk])
        form_values = {
            "category": vatech.pk,
            "name": subcategory.name,
            "slug": subcategory.slug,
            "description": subcategory.description,
            "display_order": subcategory.display_order,
            "is_active": "on",
        }

        upload = self.client.post(edit_url, {
            **form_values,
            "image": SimpleUploadedFile(
                "3d-imaging.png", tiny_png, content_type="image/png",
            ),
        })
        self.assertRedirects(upload, reverse("dashboard_subcategories"))
        subcategory.refresh_from_db()
        first_image_name = subcategory.image.name
        self.assertTrue(first_image_name.startswith("subcategories/"))
        self.assertTrue(subcategory.image.storage.exists(first_image_name))

        reopened = self.client.get(edit_url)
        self.assertContains(reopened, "Subcategory Image")
        self.assertContains(reopened, "Current image")
        self.assertContains(reopened, subcategory.image.url)

        public_page = self.client.get(
            reverse("vatech_category", args=[subcategory.slug])
        )
        self.assertContains(public_page, subcategory.image.url)
        self.assertContains(public_page, 'alt="3D Imaging"')
        self.assertNotContains(
            public_page,
            '<div class="category-visual-placeholder"><span>VD</span>',
        )

        with self.captureOnCommitCallbacks(execute=True):
            replacement = self.client.post(edit_url, {
                **form_values,
                "image": SimpleUploadedFile(
                    "3d-imaging-new.png", tiny_png, content_type="image/png",
                ),
            })
        self.assertRedirects(replacement, reverse("dashboard_subcategories"))
        subcategory.refresh_from_db()
        replacement_name = subcategory.image.name
        self.assertNotEqual(replacement_name, first_image_name)
        self.assertTrue(subcategory.image.storage.exists(replacement_name))
        self.assertFalse(subcategory.image.storage.exists(first_image_name))

        with self.captureOnCommitCallbacks(execute=True):
            removed = self.client.post(edit_url, {
                **form_values,
                "image-clear": "on",
            })
        self.assertRedirects(removed, reverse("dashboard_subcategories"))
        subcategory.refresh_from_db()
        self.assertFalse(subcategory.image)
        self.assertFalse(subcategory.image.storage.exists(replacement_name))

        fallback_page = self.client.get(
            reverse("vatech_category", args=[subcategory.slug])
        )
        self.assertContains(
            fallback_page,
            '<div class="category-visual-placeholder"><span>VD</span>',
        )

    @override_settings(STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.memory.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    })
    def test_editing_subcategory_without_new_upload_preserves_image(self):
        tiny_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
            "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        subcategory = ProductSubcategory.objects.get(
            category__slug="vatech-dental",
            slug="2d-imaging",
        )
        subcategory.image.save(
            "2d-imaging.png",
            SimpleUploadedFile(
                "2d-imaging.png", tiny_png, content_type="image/png",
            ),
            save=True,
        )
        original_name = subcategory.image.name

        response = self.client.post(
            reverse("dashboard_subcategory_edit", args=[subcategory.pk]),
            {
                "category": subcategory.category_id,
                "name": subcategory.name,
                "slug": subcategory.slug,
                "description": "Updated without replacing its image.",
                "display_order": subcategory.display_order,
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("dashboard_subcategories"))
        subcategory.refresh_from_db()
        self.assertEqual(subcategory.image.name, original_name)
        self.assertTrue(subcategory.image.storage.exists(original_name))

    @override_settings(STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.memory.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    })
    def test_customer_dashboard_manages_profile_and_multiple_media(self):
        from core.test_customer_video import test_video_bytes
        tiny_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
            "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        supplied_product = Product.objects.create(
            category=self.category,
            name="Supplied Analyzer",
            slug="supplied-analyzer",
            brand="Example Diagnostics",
            product_code="SUPPLIED-1",
            short_description="Supplied laboratory analyzer.",
            description="Supplied laboratory analyzer.",
        )
        response = self.client.post(reverse("dashboard_customer_add"), {
            "name": "Portfolio Hospital",
            "slug": "",
            "website": "https://portfolio.example/",
            "short_description": "A managed customer portfolio.",
            "description": "A complete customer profile.",
            "linkedin_url": "https://linkedin.com/company/portfolio-hospital",
            "products": [supplied_product.pk],
            "display_order": 4,
            "is_active": "on",
            "logo": SimpleUploadedFile(
                "logo.png", tiny_png, content_type="image/png",
            ),
        })
        self.assertRedirects(response, reverse("dashboard_customers"))

        customer = Customer.objects.get(slug="portfolio-hospital")
        self.assertTrue(customer.logo)
        self.assertEqual(list(customer.products.all()), [supplied_product])

        response = self.client.post(
            reverse("dashboard_customer_project_add", args=[customer.pk]),
            {
                "title": "Analyzer installation",
                "work_type": "installation",
                "description": "Installation and team training.",
                "date": "2026-08-01",
                "products": [supplied_product.pk],
                "display_order": 1,
                "project_images": [
                SimpleUploadedFile(
                    "installation.jpg", tiny_png, content_type="image/png",
                ),
                SimpleUploadedFile(
                    "training.png", tiny_png, content_type="image/png",
                ),
            ],
                "project_videos": [
                SimpleUploadedFile(
                    "project.mp4", test_video_bytes(), content_type="video/mp4",
                ),
                ],
            },
        )
        self.assertRedirects(
            response,
            reverse("dashboard_customer_projects", args=[customer.pk]),
        )
        project = CustomerProject.objects.get(customer=customer)
        self.assertEqual(project.work_type, "installation")
        self.assertEqual(list(project.products.all()), [supplied_product])
        self.assertEqual(project.media.filter(media_type="image").count(), 2)
        self.assertEqual(project.media.filter(media_type="video").count(), 1)

        uploaded_video = project.media.get(media_type="video")
        self.assertEqual(uploaded_video.video_mime_type, "video/mp4")
        self.assertTrue(uploaded_video.file.storage.exists(uploaded_video.file.name))

        uploaded_images = list(project.media.filter(media_type="image"))
        self.assertEqual(len(uploaded_images), 2)
        for uploaded_image in uploaded_images:
            self.assertTrue(
                uploaded_image.file.storage.exists(uploaded_image.file.name)
            )

        public_gallery = self.client.get(customer.get_absolute_url())
        self.assertEqual(public_gallery.status_code, 200)
        self.assertContains(public_gallery, "Work delivered")
        self.assertContains(
            public_gallery,
            '<video controls playsinline preload="metadata"',
            html=False,
        )
        self.assertContains(
            public_gallery,
            f'<source src="{reverse("customer_video_source", args=[customer.slug, uploaded_video.pk])}" type="video/mp4">',
            html=False,
        )
        for uploaded_image in uploaded_images:
            self.assertContains(
                public_gallery,
                f'data-image-src="{uploaded_image.file.url}"',
                html=False,
            )

        media_add_page = self.client.get(
            reverse(
                "dashboard_customer_project_media_add",
                args=[customer.pk, project.pk],
            )
        )
        self.assertContains(media_add_page, ".ogv,.ogg")

        media_response = self.client.post(
            reverse(
                "dashboard_customer_project_media_add",
                args=[customer.pk, project.pk],
            ),
            {
                "media_type": "video",
                "video_url": "https://vimeo.com/123456789",
                "caption": "Installation overview",
                "description": "A managed external project video.",
                "display_order": 4,
            },
        )
        self.assertRedirects(
            media_response,
            reverse(
                "dashboard_customer_project_media",
                args=[customer.pk, project.pk],
            ),
        )
        external_video = project.media.get(video_url="https://vimeo.com/123456789")
        self.assertEqual(external_video.caption, "Installation overview")
        self.assertEqual(
            external_video.embed_url,
            "https://player.vimeo.com/video/123456789",
        )

        edit_page = self.client.get(
            reverse("dashboard_customer_project_edit", args=[customer.pk, project.pk])
        )
        self.assertContains(edit_page, "Remove existing project media")
        self.assertContains(edit_page, "installation.jpg")

        replacement = self.client.post(
            reverse("dashboard_customer_edit", args=[customer.pk]),
            {
                "name": customer.name,
                "slug": customer.slug,
                "website": customer.website,
                "short_description": "Updated customer portfolio.",
                "description": customer.description,
                "linkedin_url": customer.linkedin_url,
                "products": [supplied_product.pk],
                "display_order": customer.display_order,
                "is_active": "on",
                "logo": SimpleUploadedFile(
                    "replacement.png", tiny_png, content_type="image/png",
                ),
            },
        )
        self.assertRedirects(replacement, reverse("dashboard_customers"))
        customer.refresh_from_db()
        self.assertIn("replacement", customer.logo.name)
        self.assertEqual(project.media.count(), 4)

    def test_customer_can_be_created_with_name_only(self):
        response = self.client.post(reverse("dashboard_customer_add"), {
            "name": "Name Only Hospital",
        })
        self.assertRedirects(response, reverse("dashboard_customers"))
        customer = Customer.objects.get(slug="name-only-hospital")
        self.assertFalse(customer.logo)
        self.assertEqual(customer.website, "")
        self.assertEqual(customer.short_description, "")
        self.assertEqual(customer.display_order, 0)
        self.assertFalse(customer.projects.exists())

    @override_settings(STORAGES={
        "default": {"BACKEND": "dashboard.tests.UnavailableStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    })
    def test_customer_edit_preserves_existing_logo_without_storage_access(self):
        customer = Customer.objects.create(
            name="Remote Logo Hospital",
            slug="remote-logo-hospital",
            logo="customers/logos/existing-logo.png",
            is_active=True,
        )
        response = self.client.post(
            reverse("dashboard_customer_edit", args=[customer.pk]),
            {
                "name": "Remote Logo Hospital Updated",
                "slug": customer.slug,
                "short_description": "Text-only update.",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("dashboard_customers"))
        customer.refresh_from_db()
        self.assertEqual(customer.logo.name, "customers/logos/existing-logo.png")
        self.assertEqual(customer.short_description, "Text-only update.")

    @override_settings(STORAGES={
        "default": {"BACKEND": "dashboard.tests.UnavailableStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    })
    def test_customer_upload_failure_returns_form_error_and_preserves_record(self):
        customer = Customer.objects.create(
            name="Storage Safe Hospital",
            slug="storage-safe-hospital",
            logo="customers/logos/original.png",
            short_description="Original description.",
            is_active=True,
        )
        tiny_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
            "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        response = self.client.post(
            reverse("dashboard_customer_edit", args=[customer.pk]),
            {
                "name": "Storage Safe Hospital Changed",
                "slug": customer.slug,
                "short_description": "Changed description.",
                "is_active": "on",
                "logo": SimpleUploadedFile(
                    "new-logo.png", tiny_png, content_type="image/png",
                ),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "media storage is temporarily unavailable")
        customer.refresh_from_db()
        self.assertEqual(customer.name, "Storage Safe Hospital")
        self.assertEqual(customer.logo.name, "customers/logos/original.png")
        self.assertEqual(customer.short_description, "Original description.")

    def test_partner_website_is_linked_only_from_dashboard_logo(self):
        Partner.objects.create(
            name="Example Diagnostics",
            country="Kenya",
            website="https://example.com/",
            is_active=True,
        )
        response = self.client.get(reverse("dashboard_partners"))
        self.assertContains(
            response,
            'aria-label="Visit Example Diagnostics official website"',
        )
        self.assertEqual(response.content.count(b'https://example.com/'), 1)
        self.assertNotContains(response, "Visit ↗")
        self.assertNotContains(response, "<th>Website</th>", html=True)

    def test_non_staff_cannot_access_management(self):
        self.client.logout()
        customer = User.objects.create_user("customer-two", password="test-pass-123")
        self.client.force_login(customer)
        self.assertRedirects(
            self.client.get(reverse("dashboard_products")),
            reverse("admin_login"),
        )

    def test_anonymous_admin_routes_redirect_to_admin_login(self):
        self.client.logout()
        for name in ("dashboard", "dashboard_orders", "dashboard_products"):
            self.assertRedirects(
                self.client.get(reverse(name)),
                reverse("admin_login"),
            )

    def test_admin_can_create_another_authorized_user(self):
        response = self.client.post(reverse("dashboard_user_add"), {
            "username": "sales-admin",
            "first_name": "Sales",
            "last_name": "Admin",
            "email": "sales@example.com",
            "is_active": "on",
            "is_staff": "on",
            "password1": "Strong-test-password-491",
            "password2": "Strong-test-password-491",
        })
        self.assertRedirects(response, reverse("dashboard_users"))
        user = User.objects.get(username="sales-admin")
        self.assertTrue(user.is_staff)
