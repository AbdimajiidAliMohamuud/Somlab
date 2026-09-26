from decimal import Decimal
from django.core.files.base import ContentFile
from django.db import models
from django.urls import reverse

from .labels import catalogue_display_label


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True)
    icon = models.CharField(max_length=32, default="flask")
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    menu_label = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional shorter category name for navigation menus.",
    )

    class Meta:
        ordering = ("display_order", "name")
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        if self.slug == "microbiology":
            return reverse("microbiology_landing")
        return reverse("category_detail", args=[self.slug])

    @property
    def navigation_name(self):
        return catalogue_display_label(
            self.slug,
            self.menu_label or self.name,
        )


class ProductSubcategory(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="subcategories",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
        help_text="Optional parent used for nested catalogue groups.",
    )
    name = models.CharField(max_length=140)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to="subcategories/",
        blank=True,
        help_text="Optional image used for this subcategory's public hero area.",
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("display_order", "name")
        constraints = [
            models.UniqueConstraint(
                fields=("category", "slug"),
                name="unique_product_subcategory_slug_per_category",
            ),
        ]
        verbose_name_plural = "product subcategories"

    def __str__(self):
        if self.parent_id:
            return f"{self.category.name} — {self.parent.name} — {self.name}"
        return f"{self.category.name} — {self.name}"

    def get_absolute_url(self):
        if self.category.slug == "vatech-dental":
            return reverse("vatech_category", args=[self.slug])
        return reverse(
            "subcategory_detail",
            args=[self.category.slug, self.slug],
        )


class Product(models.Model):
    AVAILABILITY = [
        ("available", "Available"),
        ("low_stock", "Low stock"),
        ("on_request", "Available on request"),
        ("unavailable", "Unavailable"),
    ]
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    subcategory = models.ForeignKey(
        ProductSubcategory,
        on_delete=models.SET_NULL,
        related_name="products",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    brand = models.CharField(max_length=120, blank=True)
    product_code = models.CharField(max_length=60, unique=True)
    short_description = models.CharField(max_length=240)
    description = models.TextField()
    specifications = models.TextField(blank=True, help_text="One specification per line.")
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to="products/", blank=True)
    source_image = models.ImageField(
        upload_to="products/originals/",
        blank=True,
        editable=False,
        help_text="Original upload retained for safe image reprocessing.",
    )
    availability = models.CharField(max_length=20, choices=AVAILABILITY, default="on_request")
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_catalogue_listing = models.BooleanField(
        default=True,
        help_text="Show this product in catalogue and subcategory product grids.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.image and not self.image._committed:
            self.image.file.seek(0)
            original = self.image.file.read()
            original_name = self.image.name
            self.source_image.save(
                original_name.rsplit("/", 1)[-1],
                ContentFile(original, name=original_name),
                save=False,
            )
            # Product artwork is presentation-ready when uploaded. Keep the
            # displayed file byte-for-byte so its canvas, background and
            # original aspect ratio are never cropped or normalized away.
            self.image = ContentFile(original, name=original_name)
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("product_detail", args=[self.slug])

    @property
    def display_brand(self):
        return catalogue_display_label(self.brand, self.brand)

    @property
    def effective_price(self):
        return self.price or Decimal("0")

    @property
    def can_order(self):
        return self.is_active and self.availability != "unavailable"


class ProductMedia(models.Model):
    MEDIA_TYPES = [
        ("image", "Image"),
        ("video", "Video"),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="gallery_media",
    )
    file = models.FileField(upload_to="products/gallery/")
    source_file = models.FileField(
        upload_to="products/gallery/originals/",
        blank=True,
        editable=False,
        help_text="Original image upload retained for safe image reprocessing.",
    )
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("display_order", "id")
        verbose_name_plural = "product media"

    def __str__(self):
        filename = self.file.name.rsplit("/", 1)[-1]
        return f"{self.get_media_type_display()}: {filename}"

    def save(self, *args, **kwargs):
        if self.media_type == "image" and self.file and not self.file._committed:
            self.file.file.seek(0)
            original = self.file.file.read()
            original_name = self.file.name
            self.source_file.save(
                original_name.rsplit("/", 1)[-1],
                ContentFile(original, name=original_name),
                save=False,
            )
            # Gallery images follow the same non-destructive upload behavior
            # as the main product image.
            self.file = ContentFile(original, name=original_name)
        return super().save(*args, **kwargs)


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    name = models.CharField(max_length=180, blank=True)
    model_number = models.CharField(max_length=120, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "id")

    def __str__(self):
        if self.name and self.model_number:
            return f"{self.name} — {self.model_number}"
        return self.name or self.model_number


class ProductRelatedItem(models.Model):
    parent_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="related_items",
    )
    child_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="parent_relations",
        null=True,
        blank=True,
    )
    image = models.ImageField(
        upload_to="products/related/",
        blank=True,
        help_text="Optional image specific to this included or related item.",
    )
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    relationship_type = models.CharField(max_length=40, default="included")
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("parent_product", "name"),
                name="unique_related_item_name_per_product",
            ),
        ]

    def __str__(self):
        return f"{self.parent_product.name} — {self.name}"
