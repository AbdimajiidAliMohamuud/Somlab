from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Max
from django.utils.text import slugify

from catalog.models import (
    Category, Product, ProductMedia, ProductSubcategory, ProductVariant,
)
from catalog.scope import public_categories
from core.models import (
    Customer, CustomerProject, CustomerProjectMedia, Partner, Service,
)
from core.customer_video import (
    MAX_VIDEO_BYTES, VIDEO_LIMIT_MESSAGE, save_video_media, validate_video_upload,
)
from orders.models import Order, ProductInquiry


class OrderUpdateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ("status", "internal_notes")
        widgets = {"internal_notes": forms.Textarea(attrs={"rows": 4})}


class InquiryUpdateForm(forms.ModelForm):
    class Meta:
        model = ProductInquiry
        fields = ("status", "internal_notes")
        widgets = {
            "internal_notes": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": "Private notes for the Somlab team",
            }),
        }


class SlugFromNameMixin:
    slug_model = None

    def clean_slug(self):
        slug = self.cleaned_data.get("slug") or slugify(self.cleaned_data.get("name", ""))
        queryset = self.slug_model.objects.filter(slug=slug)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("This URL name is already in use.")
        return slug


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        clean_one = super().clean
        if isinstance(data, (list, tuple)):
            return [clean_one(item, initial) for item in data]
        return [clean_one(data, initial)]


class ProductForm(SlugFromNameMixin, forms.ModelForm):
    slug_model = Product
    slug = forms.SlugField(required=False, help_text="Leave blank to generate it from the product name.")
    gallery_images = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={
            "accept": ".jpg,.jpeg,.png,.webp,.gif",
        }),
        help_text="Optional. Select multiple JPG, PNG, WebP or GIF images.",
    )
    gallery_videos = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={
            "accept": ".mp4,.webm,.mov,.m4v",
        }),
        help_text="Optional. Select multiple MP4, WebM, MOV or M4V videos.",
    )
    variants = forms.CharField(
        required=False,
        label="Product variants",
        widget=forms.Textarea(attrs={
            "rows": 5,
            "placeholder": "Variant name | Model number\nVariant name | Model number",
        }),
        help_text=(
            "Optional. Enter one variant per line using "
            "“Product name | Model number”."
        ),
    )
    delete_media = forms.ModelMultipleChoiceField(
        queryset=ProductMedia.objects.none(),
        required=False,
        label="Remove existing gallery media",
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = public_categories()
        self.fields["subcategory"].queryset = ProductSubcategory.objects.filter(
            is_active=True,
            category__in=public_categories(),
        ).select_related("category")
        if self.instance.pk:
            self.fields["delete_media"].queryset = self.instance.gallery_media.all()
            if not self.is_bound:
                self.initial["variants"] = "\n".join(
                    (
                        f"{variant.name} | {variant.model_number}"
                        if variant.name and variant.model_number
                        else variant.name or f"| {variant.model_number}"
                    )
                    for variant in self.instance.variants.all()
                )

    @staticmethod
    def _validate_uploads(files, allowed_extensions, maximum_files, maximum_size, label):
        if len(files) > maximum_files:
            raise forms.ValidationError(
                f"Upload no more than {maximum_files} {label.lower()} files at once."
            )
        for uploaded_file in files:
            extension = uploaded_file.name.lower().rsplit(".", 1)[-1]
            if extension not in allowed_extensions:
                raise forms.ValidationError(
                    f"{uploaded_file.name} is not a supported {label.lower()} file."
                )
            if uploaded_file.size > maximum_size:
                size_mb = maximum_size // (1024 * 1024)
                raise forms.ValidationError(
                    f"{uploaded_file.name} must be smaller than {size_mb} MB."
                )
        return files

    def clean_gallery_images(self):
        files = self._validate_uploads(
            self.cleaned_data["gallery_images"],
            {"jpg", "jpeg", "png", "webp", "gif"},
            12,
            15 * 1024 * 1024,
            "Image",
        )
        image_validator = forms.ImageField()
        return [image_validator.clean(uploaded_file) for uploaded_file in files]

    def clean_gallery_videos(self):
        return self._validate_uploads(
            self.cleaned_data["gallery_videos"],
            {"mp4", "webm", "mov", "m4v"},
            6,
            100 * 1024 * 1024,
            "Video",
        )

    def clean_variants(self):
        raw_value = self.cleaned_data.get("variants", "")
        parsed_variants = []
        seen = set()
        for line_number, line in enumerate(raw_value.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split("|", 1)]
            name = parts[0]
            model_number = parts[1] if len(parts) == 2 else ""
            if not name and not model_number:
                continue
            identity = (name.casefold(), model_number.casefold())
            if identity in seen:
                raise forms.ValidationError(
                    f"Variant on line {line_number} is duplicated."
                )
            seen.add(identity)
            parsed_variants.append((name, model_number))
        if len(parsed_variants) > 30:
            raise forms.ValidationError("Add no more than 30 product variants.")
        self._parsed_variants = parsed_variants
        return raw_value

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        subcategory = cleaned_data.get("subcategory")
        if subcategory and category and subcategory.category_id != category.pk:
            self.add_error(
                "subcategory",
                "Select a subcategory that belongs to the chosen category.",
            )
        return cleaned_data

    def save(self, commit=True):
        product = super().save(commit=commit)
        if not commit:
            return product

        for media in self.cleaned_data.get("delete_media", []):
            media.file.delete(save=False)
            media.delete()

        highest_order = product.gallery_media.aggregate(
            value=Max("display_order")
        )["value"]
        next_order = 0 if highest_order is None else highest_order + 1
        for media_type, field_name in (
            ("image", "gallery_images"),
            ("video", "gallery_videos"),
        ):
            for uploaded_file in self.cleaned_data.get(field_name, []):
                ProductMedia.objects.create(
                    product=product,
                    file=uploaded_file,
                    media_type=media_type,
                    display_order=next_order,
                )
                next_order += 1

        product.variants.all().delete()
        ProductVariant.objects.bulk_create([
            ProductVariant(
                product=product,
                name=name,
                model_number=model_number,
                display_order=index,
            )
            for index, (name, model_number) in enumerate(
                getattr(self, "_parsed_variants", [])
            )
        ])
        return product

    class Meta:
        model = Product
        fields = (
            "category", "subcategory", "name", "slug", "brand", "product_code",
            "short_description", "description", "specifications",
            "image", "availability", "is_featured", "is_active",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "specifications": forms.Textarea(attrs={"rows": 5}),
        }


class CategoryForm(SlugFromNameMixin, forms.ModelForm):
    slug_model = Category
    slug = forms.SlugField(required=False, help_text="Leave blank to generate it from the category name.")

    class Meta:
        model = Category
        fields = ("name", "menu_label", "slug", "description", "image", "display_order", "is_active")
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class ProductSubcategoryForm(forms.ModelForm):
    slug = forms.SlugField(
        required=False,
        help_text="Leave blank to generate it from the subcategory name.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = public_categories()
        self.fields["parent"].queryset = ProductSubcategory.objects.filter(
            is_active=True,
            category__in=public_categories(),
        ).exclude(pk=self.instance.pk).select_related("category")
        self.fields["image"].label = "Subcategory Image"
        self.fields["image"].required = False
        self.fields["image"].widget.attrs.update({
            "accept": ".jpg,.jpeg,.png,.webp,.gif",
        })
        self._original_image_name = (
            self.instance.image.name
            if self.instance.pk and self.instance.image
            else ""
        )

    def clean_slug(self):
        slug = self.cleaned_data.get("slug") or slugify(
            self.cleaned_data.get("name", "")
        )
        category = self.cleaned_data.get("category")
        queryset = ProductSubcategory.objects.filter(
            category=category,
            slug=slug,
        )
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError(
                "This URL name is already used within the selected category."
            )
        return slug

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and getattr(image, "size", 0) > 15 * 1024 * 1024:
            raise forms.ValidationError(
                "The subcategory image must be smaller than 15 MB."
            )
        return image

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        parent = cleaned_data.get("parent")
        if parent and category and parent.category_id != category.pk:
            self.add_error(
                "parent",
                "Select a parent subcategory from the same category.",
            )
        return cleaned_data

    def save(self, commit=True):
        subcategory = super().save(commit=False)
        if not commit:
            return subcategory

        image_changed = "image" in self.changed_data
        if self.instance.pk and not image_changed:
            subcategory.image.name = self._original_image_name

        subcategory.save()

        if (
            image_changed
            and self._original_image_name
            and self._original_image_name != subcategory.image.name
        ):
            image_storage = subcategory._meta.get_field("image").storage
            transaction.on_commit(
                lambda: image_storage.delete(self._original_image_name),
                robust=True,
            )
        return subcategory

    class Meta:
        model = ProductSubcategory
        fields = (
            "category", "parent", "name", "slug", "description", "image", "display_order",
            "is_active",
        )
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class PartnerForm(forms.ModelForm):
    def clean_menu_order(self):
        return self.cleaned_data.get("menu_order") or 0

    class Meta:
        model = Partner
        fields = (
            "name", "menu_label", "equipment_group", "menu_order",
            "menu_categories", "country", "description", "website", "logo",
            "display_order", "is_active",
        )
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}


class CustomerForm(SlugFromNameMixin, forms.ModelForm):
    slug_model = Customer
    slug = forms.SlugField(
        required=False,
        help_text="Leave blank to generate the customer page URL from the name.",
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_logo_name = (
            self.instance.logo.name if self.instance.pk and self.instance.logo else ""
        )
        for field_name in (
            "slug", "logo", "website", "short_description", "description",
            "facebook_url", "instagram_url", "linkedin_url", "youtube_url",
            "other_url", "products", "display_order", "is_active",
        ):
            self.fields[field_name].required = False
        self.fields["products"].queryset = Product.objects.select_related(
            "category"
        ).order_by("category__name", "name")

    def clean_display_order(self):
        return self.cleaned_data.get("display_order") or 0

    def save(self, commit=True):
        customer = super().save(commit=False)
        if not commit:
            return customer

        logo_changed = "logo" in self.changed_data
        if self.instance.pk and not logo_changed:
            customer.logo.name = self._original_logo_name

        customer.save()
        self.save_m2m()

        if (
            logo_changed
            and self._original_logo_name
            and self._original_logo_name != customer.logo.name
        ):
            logo_storage = customer._meta.get_field("logo").storage
            transaction.on_commit(
                lambda: logo_storage.delete(self._original_logo_name),
                robust=True,
            )

        return customer

    class Meta:
        model = Customer
        fields = (
            "name", "slug", "logo", "website", "short_description",
            "description", "facebook_url", "instagram_url", "linkedin_url",
            "youtube_url", "other_url", "products", "display_order", "is_active",
        )
        widgets = {
            "short_description": forms.Textarea(attrs={"rows": 3}),
            "description": forms.Textarea(attrs={"rows": 7}),
            "products": forms.SelectMultiple(attrs={"size": 10}),
        }


class CustomerProjectForm(forms.ModelForm):
    project_images = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={"accept": ".jpg,.jpeg,.png,.webp,.gif"}),
        help_text="Optional. Select multiple project images.",
    )
    project_videos = MultipleFileField(
        required=False,
        widget=MultipleFileInput(
            attrs={"accept": ".mp4,.webm,.mov,.m4v,.ogv,.ogg"}
        ),
        help_text="MP4, WebM, MOV/M4V or Ogg. " + VIDEO_LIMIT_MESSAGE,
    )
    delete_media = forms.ModelMultipleChoiceField(
        queryset=CustomerProjectMedia.objects.none(),
        required=False,
        label="Remove existing project media",
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in (
            "description", "date", "display_order", "project_images",
            "project_videos", "delete_media", "work_type", "products",
        ):
            self.fields[field_name].required = False
        self.fields["products"].queryset = Product.objects.select_related(
            "category"
        ).order_by("category__name", "name")
        if self.instance.pk:
            self.fields["delete_media"].queryset = self.instance.media.all()
        self.fields["project_videos"].widget.attrs["data-customer-video-limit"] = MAX_VIDEO_BYTES

    @staticmethod
    def _validate_uploads(files, allowed_extensions, maximum_files, maximum_size, label):
        if len(files) > maximum_files:
            raise forms.ValidationError(
                f"Upload no more than {maximum_files} {label.lower()} files at once."
            )
        for uploaded_file in files:
            extension = uploaded_file.name.lower().rsplit(".", 1)[-1]
            if extension not in allowed_extensions:
                raise forms.ValidationError(
                    f"{uploaded_file.name} is not a supported {label.lower()} file."
                )
            if uploaded_file.size > maximum_size:
                size_mb = maximum_size // (1024 * 1024)
                raise forms.ValidationError(
                    f"{uploaded_file.name} must be smaller than {size_mb} MB."
                )
        return files

    def clean_project_images(self):
        files = self._validate_uploads(
            self.cleaned_data["project_images"],
            {"jpg", "jpeg", "png", "webp", "gif"},
            12,
            15 * 1024 * 1024,
            "Image",
        )
        image_validator = forms.ImageField()
        return [image_validator.clean(uploaded_file) for uploaded_file in files]

    def clean_project_videos(self):
        files = self.cleaned_data["project_videos"]
        if len(files) > 6:
            raise forms.ValidationError("Upload no more than 6 video files at once.")
        return [validate_video_upload(upload) for upload in files]

    def clean_display_order(self):
        return self.cleaned_data.get("display_order") or 0

    def clean_work_type(self):
        return self.cleaned_data.get("work_type") or "project"

    def save(self, commit=True):
        project = super().save(commit=commit)
        if not commit:
            return project

        for media in self.cleaned_data.get("delete_media", []):
            storage = media.file.storage
            file_name = media.file.name
            media.delete()
            if file_name:
                transaction.on_commit(
                    lambda storage=storage, file_name=file_name: storage.delete(file_name),
                    robust=True,
                )

        highest_order = project.media.aggregate(value=Max("display_order"))["value"]
        next_order = 0 if highest_order is None else highest_order + 1
        for media_type, field_name in (
            ("image", "project_images"),
            ("video", "project_videos"),
        ):
            for uploaded_file in self.cleaned_data.get(field_name, []):
                media = CustomerProjectMedia(
                    project=project,
                    file=uploaded_file,
                    media_type=media_type,
                    display_order=next_order,
                )
                if media_type == "video":
                    save_video_media(media, uploaded_file)
                else:
                    media.save()
                next_order += 1
        return project

    class Meta:
        model = CustomerProject
        fields = (
            "title", "work_type", "description", "date", "products",
            "display_order",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "date": forms.DateInput(attrs={"type": "date"}),
            "products": forms.SelectMultiple(attrs={"size": 10}),
        }


class CustomerProjectMediaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_file_name = (
            self.instance.file.name
            if self.instance.pk and self.instance.file
            else ""
        )
        for field_name in (
            "file", "video_url", "caption", "description", "display_order",
        ):
            self.fields[field_name].required = False
        self.fields["file"].widget.attrs["accept"] = (
            ".jpg,.jpeg,.png,.webp,.gif,.mp4,.webm,.mov,.m4v,.ogv,.ogg"
        )
        self.fields["file"].help_text = (
            "Upload a JPG, PNG, WebP or GIF image, or an MP4, WebM, MOV, "
            "M4V or Ogg video. " + VIDEO_LIMIT_MESSAGE
        )
        self.fields["file"].widget.attrs["data-customer-video-limit"] = MAX_VIDEO_BYTES

    def clean_display_order(self):
        return self.cleaned_data.get("display_order") or 0

    def clean(self):
        cleaned_data = super().clean()
        media_type = cleaned_data.get("media_type")
        media_file = cleaned_data.get("file")
        video_url = cleaned_data.get("video_url")

        if media_type == "image" and not media_file:
            self.add_error("file", "Upload an image for image media.")
        if media_type == "image" and video_url:
            self.add_error("video_url", "Video URLs can only be used with video media.")
        if media_type == "video" and not media_file and not video_url:
            self.add_error("file", "Upload a video file or provide a video URL.")

        if media_file and not getattr(media_file, "_committed", False):
            extension = media_file.name.lower().rsplit(".", 1)[-1]
            if media_type == "image":
                if extension not in {"jpg", "jpeg", "png", "webp", "gif"}:
                    self.add_error("file", "Upload a JPG, PNG, WebP, or GIF image.")
                elif media_file.size > 15 * 1024 * 1024:
                    self.add_error("file", "Images must be smaller than 15 MB.")
                else:
                    try:
                        forms.ImageField().clean(media_file)
                    except forms.ValidationError as error:
                        self.add_error("file", error)
            elif media_type == "video":
                try:
                    validate_video_upload(media_file)
                except forms.ValidationError as error:
                    self.add_error("file", error)
        return cleaned_data

    def save(self, commit=True):
        media = super().save(commit=False)
        if not commit:
            return media

        file_changed = "file" in self.changed_data
        if self.instance.pk and not file_changed:
            media.file.name = self._original_file_name
        if file_changed and media.media_type == "video" and media.file:
            save_video_media(media, self.cleaned_data["file"])
        else:
            media.save()

        if (
            file_changed
            and self._original_file_name
            and self._original_file_name != media.file.name
        ):
            storage = media._meta.get_field("file").storage
            transaction.on_commit(
                lambda: storage.delete(self._original_file_name),
                robust=True,
            )
        return media

    class Meta:
        model = CustomerProjectMedia
        fields = (
            "media_type", "file", "video_url", "caption", "description",
            "display_order",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }


class ServiceForm(SlugFromNameMixin, forms.ModelForm):
    slug_model = Service
    slug = forms.SlugField(required=False, help_text="Leave blank to generate it from the service name.")

    class Meta:
        model = Service
        fields = (
            "name", "slug", "short_description", "description",
            "display_order", "is_active",
        )
        widgets = {"description": forms.Textarea(attrs={"rows": 7})}


class AdminUserCreateForm(UserCreationForm):
    class Meta:
        model = User
        fields = (
            "username", "first_name", "last_name", "email",
            "is_active", "is_staff", "password1", "password2",
        )


class AdminUserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "is_active", "is_staff")

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk and not cleaned.get("is_active") and self.instance.is_superuser:
            raise forms.ValidationError("A superuser account cannot be deactivated here.")
        return cleaned
