from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.models import Category, Product
from catalog.navigation import equipment_group_category_ids
from catalog.scope import public_products
from .email_delivery import inquiry_connection
from .forms import EAST_AFRICA_COUNTRIES, ProductInquiryForm
from .models import InquiryEmailSettings, ProductInquiry


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="Somlab Website <website@somlab.so>",
)
class ProductInquiryFlowTests(TestCase):
    def setUp(self):
        email_settings = InquiryEmailSettings.current()
        email_settings.smtp_username = "personal@gmail.com"
        email_settings.from_email = "personal@gmail.com"
        email_settings.set_app_password("example-app-password")
        email_settings.save()
        category = Category.objects.get(slug="chemistry")
        self.product = Product.objects.create(
            category=category,
            name="Test Reagent",
            slug="test-reagent",
            product_code="RG-1",
            short_description="Routine reagent.",
            description="Description",
            price="12.50",
            is_catalogue_listing=True,
        )
        self.payload = {
            "full_name": "Hassan Nur",
            "organization": "North Lab",
            "email": "hassan@example.com",
            "phone": "+252611111111",
            "country": "Somalia",
            "product_group": "laboratory",
            "product": self.product.pk,
            "quantity": 2,
            "message": "Please confirm the recommended configuration.",
            "consent": True,
        }

    def test_detail_uses_inquiry_cta_and_public_cart_ui_is_removed(self):
        response = self.client.get(self.product.get_absolute_url())
        self.assertContains(
            response,
            f'{reverse("product_inquiry")}?product={self.product.pk}',
        )
        self.assertContains(response, "Inquiry")
        self.assertNotContains(response, "Add to cart")
        self.assertNotContains(response, 'class="quantity-control"')
        self.assertNotContains(response, 'class="cart-link"')

    def test_inquiry_page_preselects_product_and_has_secure_form(self):
        response = self.client.get(
            reverse("product_inquiry"),
            {"product": self.product.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Product inquiry")
        self.assertContains(response, self.product.name)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertEqual(response.context["form"].initial["product"], self.product)
        self.assertEqual(
            response.context["form"].initial["product_group"],
            "laboratory",
        )

    def test_group_fields_use_live_catalogue_and_east_africa_countries(self):
        memberships = equipment_group_category_ids()
        response = self.client.get(reverse("product_inquiry"))
        form = response.context["form"]
        country_values = [value for value, _ in form.fields["country"].choices]
        self.assertEqual(country_values, list(EAST_AFRICA_COUNTRIES))
        self.assertEqual(
            list(form.fields["product_group"].choices)[1:],
            ProductInquiry.PRODUCT_GROUP_CHOICES,
        )
        self.assertFalse(form.fields["product"].queryset.exists())

        options_by_group = response.context["inquiry_products_by_group"]
        for group_slug in ("laboratory", "medical", "dental"):
            with self.subTest(group=group_slug):
                expected_ids = set(
                    public_products()
                    .filter(category_id__in=memberships[group_slug])
                    .values_list("pk", flat=True)
                )
                option_ids = {
                    int(option["id"])
                    for option in options_by_group[group_slug]
                }
                self.assertEqual(option_ids, expected_ids)

                bound_form = ProductInquiryForm(data={
                    "product_group": group_slug,
                })
                queryset_ids = set(
                    bound_form.fields["product"].queryset.values_list(
                        "pk",
                        flat=True,
                    )
                )
                self.assertEqual(queryset_ids, expected_ids)

    def test_product_page_prefill_detects_each_product_group(self):
        memberships = equipment_group_category_ids()
        for group_slug in ("laboratory", "medical", "dental"):
            product = (
                public_products()
                .filter(category_id__in=memberships[group_slug])
                .order_by("pk")
                .first()
            )
            self.assertIsNotNone(product)
            with self.subTest(group=group_slug):
                response = self.client.get(
                    reverse("product_inquiry"),
                    {"product": product.pk},
                )
                form = response.context["form"]
                self.assertEqual(form.initial["product_group"], group_slug)
                self.assertEqual(form.initial["product"], product)
                self.assertTrue(
                    form.fields["product"].queryset.filter(pk=product.pk).exists()
                )

    def test_product_must_belong_to_selected_group(self):
        medical_product = (
            public_products()
            .filter(
                category_id__in=equipment_group_category_ids()["medical"],
            )
            .first()
        )
        invalid = self.payload | {
            "product_group": "laboratory",
            "product": medical_product.pk,
        }
        response = self.client.post(reverse("product_inquiry"), invalid)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.assertEqual(ProductInquiry.objects.count(), 0)

    def test_valid_inquiry_is_saved_emailed_and_confirmed_with_reference(self):
        response = self.client.post(reverse("product_inquiry"), self.payload)
        self.assertRedirects(response, reverse("product_inquiry_success"))
        inquiry = ProductInquiry.objects.get()
        self.assertEqual(inquiry.status, "new")
        self.assertEqual(inquiry.product_name, self.product.name)
        self.assertEqual(inquiry.product_code, "RG-1")
        self.assertEqual(inquiry.product_category, "Chemistry")
        self.assertEqual(inquiry.product_group, "laboratory")
        self.assertEqual(inquiry.quantity, 2)
        self.assertTrue(inquiry.inquiry_number.startswith("INQ-"))

        self.assertEqual(len(mail.outbox), 1)
        notification = mail.outbox[0]
        self.assertEqual(notification.to, ["info@somlab.so"])
        self.assertEqual(notification.from_email, "personal@gmail.com")
        self.assertIn(self.product.name, notification.subject)
        self.assertIn(inquiry.inquiry_number, notification.body)
        self.assertIn("North Lab", notification.body)
        self.assertIn("Product Group: Laboratory", notification.body)

        success = self.client.get(reverse("product_inquiry_success"))
        self.assertContains(success, inquiry.inquiry_number)
        self.assertContains(success, self.product.name)

    def test_configured_recipient_receives_email_after_inquiry_is_saved(self):
        email_settings = InquiryEmailSettings.current()
        email_settings.recipient_email = "sales@somlab.so"
        email_settings.save(update_fields=["recipient_email"])

        def confirm_saved_before_send(**kwargs):
            self.assertEqual(ProductInquiry.objects.count(), 1)
            self.assertEqual(kwargs["recipient_list"], ["sales@somlab.so"])
            return 1

        with patch("orders.views.send_mail", side_effect=confirm_saved_before_send) as mocked_send:
            response = self.client.post(reverse("product_inquiry"), self.payload)
        self.assertRedirects(response, reverse("product_inquiry_success"))
        mocked_send.assert_called_once()

    def test_notifications_can_be_disabled_without_losing_inquiries(self):
        email_settings = InquiryEmailSettings.current()
        email_settings.notifications_enabled = False
        email_settings.save(update_fields=["notifications_enabled"])
        with patch("orders.views.send_mail") as mocked_send:
            response = self.client.post(reverse("product_inquiry"), self.payload)
        self.assertRedirects(response, reverse("product_inquiry_success"))
        self.assertEqual(ProductInquiry.objects.count(), 1)
        mocked_send.assert_not_called()

    def test_smtp_connection_uses_decrypted_settings_without_storing_plaintext(self):
        email_settings = InquiryEmailSettings.current()
        email_settings.smtp_host = "smtp.gmail.com"
        email_settings.smtp_port = 587
        email_settings.use_tls = True
        email_settings.save()
        self.assertNotIn("example-app-password", email_settings.app_password_encrypted)
        with patch("orders.email_delivery.get_connection") as mocked_connection:
            inquiry_connection(email_settings)
        self.assertEqual(mocked_connection.call_args.kwargs["host"], "smtp.gmail.com")
        self.assertEqual(mocked_connection.call_args.kwargs["port"], 587)
        self.assertTrue(mocked_connection.call_args.kwargs["use_tls"])
        self.assertEqual(mocked_connection.call_args.kwargs["username"], "personal@gmail.com")
        self.assertEqual(mocked_connection.call_args.kwargs["password"], "example-app-password")

    @patch("orders.views.send_mail", side_effect=RuntimeError("example-app-password"))
    def test_email_failure_never_loses_valid_inquiry(self, mocked_send):
        with self.assertLogs("orders.views", level="ERROR") as logs:
            response = self.client.post(reverse("product_inquiry"), self.payload)
        self.assertRedirects(response, reverse("product_inquiry_success"))
        self.assertEqual(ProductInquiry.objects.count(), 1)
        self.assertNotIn("example-app-password", " ".join(logs.output))
        mocked_send.assert_called_once()

    @patch("orders.views.send_mail", return_value=0)
    def test_zero_delivery_is_logged_and_inquiry_remains_saved(self, mocked_send):
        with self.assertLogs("orders.views", level="ERROR") as logs:
            response = self.client.post(reverse("product_inquiry"), self.payload)
        self.assertRedirects(response, reverse("product_inquiry_success"))
        self.assertEqual(ProductInquiry.objects.count(), 1)
        self.assertIn("not delivered", logs.output[0])
        mocked_send.assert_called_once()

    def test_invalid_submission_shows_errors_and_saves_nothing(self):
        invalid = self.payload | {"email": "not-an-email", "quantity": 0}
        response = self.client.post(reverse("product_inquiry"), invalid)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a valid email address")
        self.assertContains(response, "Enter a quantity of 1 or more")
        self.assertEqual(ProductInquiry.objects.count(), 0)

    def test_non_public_products_cannot_be_selected(self):
        hidden_category = Category.objects.create(
            name="Hidden Category",
            slug="hidden-inquiry-category",
            is_active=True,
        )
        hidden_product = Product.objects.create(
            category=hidden_category,
            name="Hidden Product",
            slug="hidden-inquiry-product",
            is_active=True,
        )
        self.assertEqual(
            self.client.get(
                reverse("product_inquiry"),
                {"product": hidden_product.pk},
            ).status_code,
            404,
        )
        invalid = self.payload | {"product": hidden_product.pk}
        response = self.client.post(reverse("product_inquiry"), invalid)
        self.assertContains(response, "Select a valid choice")
        self.assertEqual(ProductInquiry.objects.count(), 0)

    def test_legacy_public_cart_routes_redirect_to_catalogue_or_inquiry(self):
        self.assertRedirects(
            self.client.get(reverse("cart_detail")),
            reverse("product_list"),
        )
        add_response = self.client.post(
            reverse("cart_add", args=[self.product.pk]),
        )
        self.assertEqual(add_response.status_code, 302)
        self.assertEqual(
            add_response.url,
            f'{reverse("product_inquiry")}?product={self.product.pk}',
        )
        self.assertRedirects(
            self.client.get(reverse("checkout")),
            reverse("product_list"),
        )

    def test_dashboard_search_detail_and_status_update(self):
        inquiry = ProductInquiry.objects.create(
            product=self.product,
            full_name="Hassan Nur",
            organization="North Lab",
            email="hassan@example.com",
            phone="+252611111111",
            country="Somalia",
            message="Configuration request",
        )
        staff = User.objects.create_user(
            "staff",
            password="test-pass-123",
            is_staff=True,
        )
        self.client.force_login(staff)
        dashboard = self.client.get(reverse("dashboard"))
        self.assertContains(dashboard, inquiry.inquiry_number)
        listing = self.client.get(reverse("dashboard_inquiries"), {"q": "North Lab"})
        self.assertContains(listing, inquiry.inquiry_number)
        detail_url = reverse("dashboard_inquiry_detail", args=[inquiry.inquiry_number])
        detail = self.client.get(detail_url)
        self.assertContains(detail, "Configuration request")
        self.assertContains(detail, "Laboratory")
        response = self.client.post(detail_url, {
            "status": "in_progress",
            "internal_notes": "Quotation preparation assigned.",
        })
        self.assertRedirects(response, detail_url)
        inquiry.refresh_from_db()
        self.assertEqual(inquiry.status, "in_progress")
        self.assertEqual(inquiry.internal_notes, "Quotation preparation assigned.")

    def test_product_deletion_preserves_inquiry_snapshot(self):
        inquiry = ProductInquiry.objects.create(
            product=self.product,
            full_name="Hassan Nur",
            organization="North Lab",
            email="hassan@example.com",
            phone="+252611111111",
            message="Archived product request",
        )
        self.product.delete()
        inquiry.refresh_from_db()
        self.assertIsNone(inquiry.product)
        self.assertEqual(inquiry.product_name, "Test Reagent")
        self.assertEqual(inquiry.product_code, "RG-1")

    def test_non_staff_cannot_view_inquiry_dashboard(self):
        user = User.objects.create_user("customer", password="test-pass-123")
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard_inquiries"))
        self.assertRedirects(response, reverse("admin_login"))
