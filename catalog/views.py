from math import gcd
from urllib.parse import urlencode

from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_GET
from core.models import Partner
from .ibreastexam import IBREASTEXAM_FEATURES, IBREASTEXAM_PRODUCT_CODE
from .labels import catalogue_display_label
from .models import ProductSubcategory
from .navigation import EQUIPMENT_GROUPS, equipment_group_category_ids
from .microbiology import (
    MICROBIOLOGY_CATEGORY_SLUG,
    MICROBIOLOGY_GROUPS,
)
from .molbio_source import ASSAY_GROUPS
from .scope import public_categories, public_products
from .search import search_public_products


MES_CATEGORY_SLUG = "medical-electronic-systems"
GROUP_ROTATION_SESSION_KEY = "catalogue_group_rotation_offsets"


def catalogue_listing_products():
    """Return public products intended for catalogue and subcategory grids."""
    return public_products().filter(is_catalogue_listing=True)


def rotate_group_products(request, slug, products):
    """Rotate a complete group listing without changing its membership."""
    product_count = len(products)
    if product_count < 2:
        return products

    step = max(1, product_count // 3)
    while gcd(step, product_count) != 1:
        step += 1

    stored_offsets = request.session.get(GROUP_ROTATION_SESSION_KEY, {})
    offsets = dict(stored_offsets) if isinstance(stored_offsets, dict) else {}
    try:
        previous_offset = int(offsets.get(slug, 0))
    except (TypeError, ValueError):
        previous_offset = 0
    offset = (previous_offset + step) % product_count
    offsets[slug] = offset
    request.session[GROUP_ROTATION_SESSION_KEY] = offsets
    return products[offset:] + products[:offset]


def build_brand_groups(public_catalogue):
    partner_names = {
        slugify(name): catalogue_display_label(name, name)
        for name in Partner.objects.filter(is_active=True).values_list(
            "name", flat=True
        )
    }
    brand_groups = {
        brand_slug: {
            "slug": brand_slug,
            "name": partner_name,
            "values": [],
        }
        for brand_slug, partner_name in partner_names.items()
        if brand_slug
    }
    for brand_name in (
        public_catalogue.exclude(brand="")
        .order_by("brand")
        .values_list("brand", flat=True)
        .distinct()
    ):
        brand_slug = slugify(brand_name)
        if not brand_slug:
            continue
        group = brand_groups.setdefault(brand_slug, {
            "slug": brand_slug,
            "name": catalogue_display_label(
                brand_name,
                partner_names.get(brand_slug, brand_name),
            ),
            "values": [],
        })
        group["values"].append(brand_name)
    return partner_names, brand_groups


def filter_products_by_brand(products, selected_brand, brand_groups):
    selected_brand_group = brand_groups.get(selected_brand)
    if not selected_brand:
        return products, selected_brand_group
    if not selected_brand_group or not selected_brand_group["values"]:
        return products.none(), selected_brand_group

    brand_query = Q()
    for brand_value in selected_brand_group["values"]:
        brand_query |= Q(brand__iexact=brand_value)
    return products.filter(brand_query), selected_brand_group


def resolve_brand_name(selected_brand, partner_names, selected_brand_group):
    if not selected_brand:
        return ""
    return (
        partner_names.get(selected_brand)
        or (selected_brand_group and selected_brand_group["name"])
        or selected_brand.replace("-", " ").title()
    )


def ordered_microbiology_products(products, group):
    """Return a group queryset ordered by its stable product-code mapping."""
    product_codes = group["product_codes"]
    if not product_codes:
        return products.none()
    configured_order = Case(
        *(
            When(product_code=product_code, then=Value(index))
            for index, product_code in enumerate(product_codes)
        ),
        default=Value(len(product_codes)),
        output_field=IntegerField(),
    )
    return products.filter(product_code__in=product_codes).order_by(
        configured_order,
        "name",
    )


def microbiology_catalogue_context(request):
    """Build the four-card Microbiology landing context."""
    category = get_object_or_404(
        public_categories(),
        slug=MICROBIOLOGY_CATEGORY_SLUG,
    )
    public_catalogue = public_products()
    microbiology_catalogue = public_catalogue.filter(
        category=category,
    ).select_related("category")
    selected_brand = slugify(request.GET.get("brand", "").strip())
    partner_names, brand_groups = build_brand_groups(public_catalogue)
    filtered_catalogue, selected_brand_group = filter_products_by_brand(
        microbiology_catalogue,
        selected_brand,
        brand_groups,
    )
    selected_brand_name = resolve_brand_name(
        selected_brand,
        partner_names,
        selected_brand_group,
    )
    solution_groups = []
    for configured_group in MICROBIOLOGY_GROUPS:
        filtered_group_products = list(ordered_microbiology_products(
            filtered_catalogue,
            configured_group,
        ))
        image_product = next(
            (product for product in filtered_group_products if product.image),
            None,
        )
        solution_groups.append({
            **configured_group,
            "products": filtered_group_products,
            "image_product": image_product,
        })

    return {
        "category": category,
        "fallback_image": category.image,
        "selected_brand": selected_brand,
        "selected_brand_name": selected_brand_name,
        "solution_groups": solution_groups,
    }


def product_list(request):
    public_catalogue = catalogue_listing_products()
    products = public_catalogue.select_related("category")
    categories = public_categories().annotate(
        public_product_count=Count(
            "products",
            filter=(
                Q(products__is_active=True)
                & Q(products__is_catalogue_listing=True)
            ),
            distinct=True,
        )
    ).order_by("display_order", "name")
    selected_category = request.GET.get("category", "")
    selected_brand = slugify(request.GET.get("brand", "").strip())
    query = request.GET.get("q", "").strip()
    availability = request.GET.get("availability", "")

    partner_names, brand_groups = build_brand_groups(public_catalogue)

    if selected_category:
        products = products.filter(category__slug=selected_category)
    if query:
        products = search_public_products(query, queryset=products)
    products, selected_brand_group = filter_products_by_brand(
        products, selected_brand, brand_groups
    )
    if availability:
        products = products.filter(availability=availability)

    current_parameters = {
        "q": query,
        "category": selected_category,
        "brand": selected_brand,
    }

    def catalogue_url(**updates):
        parameters = {**current_parameters, **updates}
        parameters = {
            key: value for key, value in parameters.items() if value
        }
        base_url = reverse("product_list")
        return f"{base_url}?{urlencode(parameters)}" if parameters else base_url

    category_links = [
        {
            "category": category,
            # Choosing a category starts a new catalogue context. Do not carry
            # a manufacturer selected on the previous catalogue page.
            "url": category.get_absolute_url(),
        }
        for category in categories
    ]
    brand_links = [
        {
            "name": brand["name"],
            "slug": brand["slug"],
            # Manufacturer navigation also replaces the previous context
            # rather than combining with a stale category or search query.
            "url": (
                f"{reverse('product_list')}?"
                f"{urlencode({'brand': brand['slug']})}"
            ),
        }
        for brand in sorted(
            brand_groups.values(), key=lambda item: item["name"].lower()
        )
    ]

    selected_brand_name = resolve_brand_name(
        selected_brand, partner_names, selected_brand_group
    )

    product_groups = []
    # Keep both the complete catalogue and a manufacturer-only catalogue
    # grouped by the existing product categories. Search, availability and
    # category filters retain their compact results-grid presentation.
    if not any((selected_category, query, availability)):
        grouped_products = {category.pk: [] for category in categories}
        for product in products:
            grouped_products.setdefault(product.category_id, []).append(product)
        product_groups = [
            {"category": category, "products": grouped_products[category.pk]}
            for category in categories
            if grouped_products[category.pk]
        ]

    return render(request, "catalog/product_list.html", {
        "products": products,
        "categories": categories,
        "category_links": category_links,
        "brand_links": brand_links,
        "selected_category": selected_category,
        "selected_brand": selected_brand,
        "selected_brand_name": selected_brand_name,
        "all_categories_url": reverse("product_list"),
        "clear_brand_url": catalogue_url(brand=""),
        "query": query,
        "availability": availability,
        "product_groups": product_groups,
    })


def equipment_group_products(request, slug):
    group_names = {
        group_slug: group_name
        for group_slug, group_name, _ in EQUIPMENT_GROUPS
    }
    group_name = group_names.get(slug)
    if group_name is None:
        raise Http404("Equipment group not found")

    category_ids = equipment_group_category_ids()[slug]
    categories = list(
        public_categories()
        .filter(pk__in=category_ids)
        .order_by("display_order", "name")
    )
    products = list(
        catalogue_listing_products()
        .filter(category_id__in=category_ids)
        .select_related("category", "subcategory")
        .order_by("name", "pk")
        .distinct()
    )
    products = rotate_group_products(request, slug, products)
    return render(request, "catalog/equipment_group_products.html", {
        "equipment_group_slug": slug,
        "equipment_group_name": group_name,
        "categories": categories,
        "products": products,
    })


@require_GET
def product_suggestions(request):
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"results": []})

    products = search_public_products(
        query,
        queryset=catalogue_listing_products().select_related("category"),
    )[:6]
    results = []
    for product in products:
        results.append({
            "name": product.name,
            "brand": product.display_brand or product.category.navigation_name,
            "category": product.category.navigation_name,
            "product_code": product.product_code,
            "thumbnail": product.image.url if product.image else "",
            "url": product.get_absolute_url(),
        })

    return JsonResponse({"results": results})


def zeiss_microscopy(request):
    return render(request, "catalog/zeiss_microscopy.html")


def microbiology_landing(request):
    context = microbiology_catalogue_context(request)
    context["clear_brand_url"] = reverse("microbiology_landing")
    return render(request, "catalog/microbiology_landing.html", context)


def _render_subcategory_detail(request, category, slug):
    subcategory = get_object_or_404(
        ProductSubcategory,
        category=category,
        slug=slug,
        is_active=True,
    )
    products_query = (
        catalogue_listing_products()
        .filter(category=category, subcategory=subcategory)
        .select_related("category", "subcategory")
    )
    is_truenat_assay_group = (
        category.slug == "molbio"
        and subcategory.parent_id is not None
        and subcategory.parent.slug == "truenat-assays"
    )
    if is_truenat_assay_group:
        official_names = ASSAY_GROUPS.get(subcategory.name, ())
        official_order = Case(
            *(
                When(name=name, then=Value(index))
                for index, name in enumerate(official_names)
            ),
            default=Value(len(official_names)),
            output_field=IntegerField(),
        )
        products = list(products_query.order_by(official_order, "name"))
    else:
        products = list(products_query.order_by(
            "id" if category.slug == MES_CATEGORY_SLUG else "name"
        ))
    child_subcategories = list(
        subcategory.children.filter(is_active=True)
        .annotate(product_total=Count("products"))
        .order_by("display_order", "name")
    )
    return render(request, "catalog/subcategory_detail.html", {
        "category": category,
        "subcategory": subcategory,
        "products": products,
        "child_subcategories": child_subcategories,
        "is_truenat_assay_group": is_truenat_assay_group,
        "is_vatech": category.slug == "vatech-dental",
    })


def subcategory_detail(request, category_slug, slug):
    category = get_object_or_404(public_categories(), slug=category_slug)
    return _render_subcategory_detail(request, category, slug)


def vatech_category(request, slug):
    category = get_object_or_404(
        public_categories(),
        slug="vatech-dental",
    )
    return _render_subcategory_detail(request, category, slug)


def category_detail(request, slug):
    if slug == MICROBIOLOGY_CATEGORY_SLUG:
        destination = reverse("microbiology_landing")
        if request.META.get("QUERY_STRING"):
            destination = f"{destination}?{request.META['QUERY_STRING']}"
        return redirect(destination)

    category = get_object_or_404(public_categories(), slug=slug)
    public_catalogue = catalogue_listing_products()
    products = public_catalogue.filter(category=category).select_related("category")
    selected_brand = slugify(request.GET.get("brand", "").strip())
    partner_names, brand_groups = build_brand_groups(public_catalogue)
    products, selected_brand_group = filter_products_by_brand(
        products, selected_brand, brand_groups
    )
    selected_brand_name = resolve_brand_name(
        selected_brand, partner_names, selected_brand_group
    )
    subcategory_groups = []
    for subcategory in ProductSubcategory.objects.filter(
        category=category,
        is_active=True,
        parent__isnull=True,
    ):
        grouped_query = products.filter(
            Q(subcategory=subcategory) | Q(subcategory__parent=subcategory)
        )
        if category.slug == MES_CATEGORY_SLUG:
            grouped_query = grouped_query.order_by("id")
        grouped_products = list(grouped_query)
        if grouped_products:
            subcategory_groups.append({
                "subcategory": subcategory,
                "products": grouped_products,
            })
    brand_products_url = ""
    if selected_brand:
        brand_products_url = (
            f"{reverse('product_list')}?"
            f"{urlencode({'brand': selected_brand})}"
        )
    return render(request, "catalog/category_detail.html", {
        "category": category,
        "products": products,
        "selected_brand": selected_brand,
        "selected_brand_name": selected_brand_name,
        "brand_products_url": brand_products_url,
        "clear_brand_url": category.get_absolute_url(),
        "subcategory_groups": subcategory_groups,
    })


def product_detail(request, slug):
    product = get_object_or_404(
        public_products()
        .select_related("category", "subcategory")
        .prefetch_related(
            "gallery_media",
            "variants",
            "related_items__child_product",
        ),
        slug=slug,
    )
    related = list(
        public_products()
        .filter(
            category=product.category,
            subcategory=product.subcategory,
            is_catalogue_listing=True,
        )
        .exclude(pk=product.pk)
        .annotate(
            recommendation_status_order=Case(
                When(availability="unavailable", then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by("recommendation_status_order", "-name")
    )
    nested_items = list(product.related_items.all())
    show_included_related = bool(nested_items or related)
    gallery_items = []
    if product.image:
        main_image = product.source_image or product.image
        gallery_items.append({
            "media_type": "image",
            "url": main_image.url,
            "fallback_url": product.image.url if main_image != product.image else "",
            "label": f"{product.name} main image",
        })
    gallery_media = list(product.gallery_media.all())
    for media in gallery_media:
        display_file = (
            media.source_file
            if media.media_type == "image" and media.source_file
            else media.file
        )
        gallery_items.append({
            "media_type": media.media_type,
            "url": display_file.url,
            "fallback_url": (
                media.file.url if display_file != media.file else ""
            ),
            "label": f"{product.name} {media.get_media_type_display().lower()}",
        })
    product_feature_sections = []
    if product.product_code == IBREASTEXAM_PRODUCT_CODE:
        media_by_order = {
            media.display_order: media
            for media in gallery_media
            if media.media_type == "image" and media.file
        }
        for feature in IBREASTEXAM_FEATURES:
            media = media_by_order.get(feature["display_order"])
            if media:
                product_feature_sections.append({
                    "title": feature["title"],
                    "description": feature["description"],
                    "image_url": media.file.url,
                    "source_url": feature["source_url"],
                })
    return render(request, "catalog/product_detail.html", {
        "product": product,
        "related": related,
        "gallery_items": gallery_items,
        "product_feature_sections": product_feature_sections,
        "variants": product.variants.all(),
        "nested_items": nested_items,
        "show_included_related": show_included_related,
        "product_section_count": (
            1 + int(bool(product.specifications)) + int(show_included_related)
        ),
        "is_mes_product": product.category.slug == MES_CATEGORY_SLUG,
        "hide_related_item_specifications": product.product_code == "SQA-iOw",
    })
