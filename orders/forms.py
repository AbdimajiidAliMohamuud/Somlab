from django import forms
from catalog.navigation import (
    equipment_group_category_ids,
    equipment_group_for_category,
)
from catalog.scope import public_products

from .models import Order, ProductInquiry


EAST_AFRICA_COUNTRIES = (
    "Somalia",
    "Kenya",
    "Ethiopia",
    "Djibouti",
    "Eritrea",
    "Uganda",
    "Tanzania",
    "Rwanda",
    "Burundi",
    "South Sudan",
)


class ProductInquiryForm(forms.ModelForm):
    product_group = forms.ChoiceField(
        choices=(
            ("", "Select a product group"),
            *ProductInquiry.PRODUCT_GROUP_CHOICES,
        ),
        required=True,
        label="Product Group",
    )
    country = forms.ChoiceField(
        choices=tuple((country, country) for country in EAST_AFRICA_COUNTRIES),
        required=True,
    )
    consent = forms.BooleanField(
        required=True,
        label=(
            "I confirm these details are correct and agree to be contacted "
            "by Somlab about this inquiry."
        ),
    )

    class Meta:
        model = ProductInquiry
        fields = (
            "full_name",
            "organization",
            "email",
            "phone",
            "country",
            "product_group",
            "product",
            "quantity",
            "message",
            "consent",
        )
        labels = {
            "organization": "Organization / Company",
            "quantity": "Quantity needed (optional)",
            "message": "Message / Requirements",
        }
        widgets = {
            "quantity": forms.NumberInput(attrs={"min": 1, "max": 999999}),
            "message": forms.Textarea(attrs={
                "rows": 6,
                "placeholder": (
                    "Tell us about the product, application, delivery, or "
                    "technical requirements."
                ),
            }),
        }

    def __init__(self, *args, product=None, group_memberships=None, **kwargs):
        super().__init__(*args, **kwargs)
        memberships = group_memberships or equipment_group_category_ids()
        self.group_memberships = memberships
        selected_group = ""
        if self.is_bound:
            selected_group = self.data.get(
                self.add_prefix("product_group"),
                "",
            )
        elif product is not None:
            selected_group = equipment_group_for_category(
                product.category_id,
                memberships,
            )
            self.initial["product_group"] = selected_group
        else:
            selected_group = self.initial.get("product_group", "")

        products = public_products().select_related("category").order_by("name")
        if selected_group in memberships:
            products = products.filter(
                category_id__in=memberships[selected_group],
            )
        else:
            products = products.none()
        self.fields["product"].queryset = products
        self.fields["product"].required = True
        self.fields["product"].empty_label = "Select a product"
        self.fields["quantity"].widget.attrs["min"] = 1
        if product is not None and not self.is_bound:
            self.initial["product"] = product

    def clean(self):
        cleaned_data = super().clean()
        product_group = cleaned_data.get("product_group")
        product = cleaned_data.get("product")
        if product_group and product:
            if product.category_id not in self.group_memberships.get(
                product_group,
                (),
            ):
                self.add_error(
                    "product",
                    "Select a product from the chosen product group.",
                )
        return cleaned_data

    def clean_quantity(self):
        quantity = self.cleaned_data.get("quantity")
        if quantity is not None and quantity < 1:
            raise forms.ValidationError("Enter a quantity of 1 or more.")
        if quantity is not None and quantity > 999999:
            raise forms.ValidationError("Enter a quantity of 999,999 or less.")
        return quantity


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = (
            "full_name", "company_name", "email", "phone", "country",
            "city", "delivery_address", "notes",
        )
        widgets = {
            "delivery_address": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Products, delivery, or contact instructions"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_authenticated:
            self.fields["full_name"].initial = user.get_full_name()
            self.fields["email"].initial = user.email
