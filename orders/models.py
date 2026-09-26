from decimal import Decimal
import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from catalog.navigation import EQUIPMENT_GROUPS, equipment_group_for_category


def generate_inquiry_number():
    """Return a non-sequential public reference safe to display to customers."""
    return f"INQ-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"


class ProductInquiry(models.Model):
    STATUS_CHOICES = [
        ("new", "New"),
        ("in_progress", "In Progress"),
        ("responded", "Responded"),
        ("closed", "Closed"),
    ]
    PRODUCT_GROUP_CHOICES = [
        (slug, name) for slug, name, _ in EQUIPMENT_GROUPS
    ]

    inquiry_number = models.CharField(
        max_length=32,
        unique=True,
        editable=False,
        default=generate_inquiry_number,
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inquiries",
    )
    product_group = models.CharField(
        max_length=20,
        choices=PRODUCT_GROUP_CHOICES,
        blank=True,
        default="",
    )
    product_name = models.CharField(max_length=180)
    product_code = models.CharField(max_length=60)
    product_category = models.CharField(max_length=120)
    full_name = models.CharField(max_length=120)
    organization = models.CharField(max_length=160)
    email = models.EmailField()
    phone = models.CharField(max_length=40)
    country = models.CharField(max_length=80, default="Somalia")
    quantity = models.PositiveIntegerField(null=True, blank=True)
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="new",
    )
    internal_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status", "created_at")),
        ]

    def __str__(self):
        return self.inquiry_number

    def save(self, *args, **kwargs):
        if self.product_id and (self._state.adding or not self.product_name):
            self.product_name = self.product.name
            self.product_code = self.product.product_code
            self.product_category = self.product.category.navigation_name
        if self.product_id and not self.product_group:
            self.product_group = equipment_group_for_category(
                self.product.category_id,
            )
        super().save(*args, **kwargs)


class Order(models.Model):
    STATUS_CHOICES = [
        ("new", "New"),
        ("contacted", "Contacted"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("ready", "Ready"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    order_number = models.CharField(max_length=24, unique=True, editable=False)
    full_name = models.CharField(max_length=120)
    company_name = models.CharField(max_length=160, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=40)
    country = models.CharField(max_length=80, default="Somalia")
    city = models.CharField(max_length=80)
    delivery_address = models.TextField()
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            from django.utils import timezone
            prefix = timezone.now().strftime("SL%y%m")
            last = Order.objects.filter(order_number__startswith=prefix).order_by("-order_number").first()
            sequence = int(last.order_number.rsplit("-", 1)[-1]) + 1 if last else 1
            self.order_number = f"{prefix}-{sequence:05d}"
        super().save(*args, **kwargs)

    def recalculate_total(self):
        self.total_amount = sum(
            (item.subtotal for item in self.items.all()), Decimal("0")
        )
        self.save(update_fields=["total_amount", "updated_at"])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.SET_NULL, null=True, related_name="order_items"
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    product_name = models.CharField(max_length=180)
    product_code = models.CharField(max_length=60)
    variant_name = models.CharField(max_length=180, blank=True)
    variant_model_number = models.CharField(max_length=120, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"

    @property
    def selected_variant_label(self):
        if self.variant_name and self.variant_model_number:
            return f"{self.variant_name} — Model {self.variant_model_number}"
        if self.variant_model_number:
            return f"Model {self.variant_model_number}"
        return self.variant_name

    def save(self, *args, **kwargs):
        if self.variant_id:
            if not self.variant_name:
                self.variant_name = self.variant.name
            if not self.variant_model_number:
                self.variant_model_number = self.variant.model_number
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)
