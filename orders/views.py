import logging
from urllib.parse import urljoin

from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST

from catalog.navigation import (
    EQUIPMENT_GROUPS,
    equipment_group_category_ids,
    equipment_group_for_category,
)
from catalog.scope import public_products
from .forms import ProductInquiryForm
from .email_delivery import inquiry_connection
from .models import InquiryEmailSettings, ProductInquiry


logger = logging.getLogger(__name__)
SITE_ORIGIN = "https://somlab.so/"


def _send_inquiry_notification(inquiry):
    email_settings = InquiryEmailSettings.current()
    if not email_settings.notifications_enabled:
        return
    connection = inquiry_connection(email_settings)
    submitted = inquiry.created_at.strftime("%d %b %Y, %H:%M %Z")
    context = {
        "inquiry": inquiry,
        "submitted": submitted,
        "admin_url": urljoin(
            SITE_ORIGIN,
            reverse("dashboard_inquiry_detail", args=[inquiry.inquiry_number]).lstrip("/"),
        ),
        # The stable, public URL is reachable by email clients independently
        # of a deployment's generated staticfiles manifest.
        "logo_url": urljoin(SITE_ORIGIN, "static/img/somlab-logo.png"),
    }
    delivered = send_mail(
        subject=f"New Product Inquiry – {inquiry.product_name}",
        message=render_to_string("orders/email/product_inquiry.txt", context),
        from_email=email_settings.from_email,
        recipient_list=[email_settings.recipient_email],
        fail_silently=False,
        connection=connection,
        html_message=render_to_string("orders/email/product_inquiry.html", context),
    )
    if delivered != 1:
        logger.error(
            "Inquiry notification was not delivered for %s",
            inquiry.inquiry_number,
        )


def product_inquiry(request):
    group_memberships = equipment_group_category_ids()
    product = None
    product_id = request.GET.get("product", "").strip()
    if product_id:
        product = get_object_or_404(public_products(), pk=product_id)

    form = ProductInquiryForm(
        request.POST or None,
        product=product,
        group_memberships=group_memberships,
    )
    if request.method == "POST" and form.is_valid():
        inquiry = form.save()
        request.session["last_inquiry_id"] = inquiry.pk
        try:
            _send_inquiry_notification(inquiry)
        except Exception as error:
            logger.error(
                "Inquiry notification failed for %s (%s)",
                inquiry.inquiry_number,
                type(error).__name__,
            )
        return redirect("product_inquiry_success")

    products_by_group = {slug: [] for slug, _, _ in EQUIPMENT_GROUPS}
    for option_product in (
        public_products()
        .only("id", "name", "category_id")
        .order_by("name", "pk")
    ):
        group_slug = equipment_group_for_category(
            option_product.category_id,
            group_memberships,
        )
        if group_slug:
            products_by_group[group_slug].append({
                "id": str(option_product.pk),
                "name": option_product.name,
            })

    return render(request, "orders/product_inquiry.html", {
        "form": form,
        "selected_product": product,
        "inquiry_products_by_group": products_by_group,
    })


def product_inquiry_success(request):
    inquiry_id = request.session.get("last_inquiry_id")
    if not inquiry_id:
        return redirect("product_list")
    inquiry = get_object_or_404(ProductInquiry, pk=inquiry_id)
    return render(request, "orders/product_inquiry_success.html", {
        "inquiry": inquiry,
    })


def cart_detail(request):
    messages.info(request, "Somlab now accepts product inquiries directly from each product page.")
    return redirect("product_list")


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(public_products(), pk=product_id)
    return redirect(f"{reverse('product_inquiry')}?product={product.pk}")


@require_POST
def cart_update(request, line_key):
    return redirect("product_list")


@require_POST
def cart_remove(request, line_key):
    return redirect("product_list")


def checkout(request):
    messages.info(request, "Checkout has been replaced by Somlab product inquiries.")
    return redirect("product_list")


def order_success(request):
    return redirect("product_list")
