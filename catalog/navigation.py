from django.utils.text import slugify
from django.urls import reverse

from core.models import Partner

from .labels import LABORATORY_DISPLAY_LABELS
from .scope import public_categories


EQUIPMENT_GROUPS = (
    ("laboratory", "Laboratory", "laboratory-menu-heading"),
    ("medical", "Medical Equipment", "medical-equipment-menu-heading"),
    ("dental", "Dental Equipment", "dental-equipment-menu-heading"),
)

LABORATORY_MENU_ITEMS = (
    ("Chemistry", "category", "chemistry"),
    ("Immunoassay", "category", "immunoassay"),
    ("Hematology", "category", "hematology"),
    ("Urinalysis", "category", "urinalysis"),
    ("Microbiology", "category", "microbiology"),
    ("Blood Banking", "category", "blood-banking"),
    (LABORATORY_DISPLAY_LABELS["polycheck"], "category", "polycheck"),
    (LABORATORY_DISPLAY_LABELS["molbio"], "category", "molbio"),
    (
        LABORATORY_DISPLAY_LABELS["medical-electronic-systems"],
        "category",
        "medical-electronic-systems",
    ),
    (
        LABORATORY_DISPLAY_LABELS["ama-helic-ubt-reader"],
        "category",
        "ama-helic-ubt-reader",
    ),
    (
        LABORATORY_DISPLAY_LABELS["sd-biosensor"],
        "category",
        "sd-biosensor",
    ),
    (
        LABORATORY_DISPLAY_LABELS["eschweiler-abg"],
        "category",
        "eschweiler-abg",
    ),
)

EXPANDABLE_LABORATORY_CATEGORIES = {
    "polycheck",
    "molbio",
    "medical-electronic-systems",
    "ama-helic-ubt-reader",
    "sd-biosensor",
    "eschweiler-abg",
}

LABORATORY_CHILD_LABELS = {
    ("eschweiler-abg", "modular-pro"): "Modular Pro",
    ("eschweiler-abg", "combi-line-2"): "Combi Line 2",
}


def equipment_group_category_ids():
    """Return the live category membership for each equipment group."""
    categories = list(public_categories().only("id", "slug"))
    category_ids_by_slug = {
        category.slug: category.pk for category in categories
    }
    memberships = {
        group_slug: set() for group_slug, _, _ in EQUIPMENT_GROUPS
    }
    memberships["laboratory"].update(
        category_ids_by_slug[destination]
        for _, destination_type, destination in LABORATORY_MENU_ITEMS
        if destination_type == "category" and destination in category_ids_by_slug
    )

    for partner in (
        Partner.objects.filter(
            is_active=True,
            equipment_group__in=("medical", "dental"),
        )
        .prefetch_related("menu_categories")
    ):
        memberships[partner.equipment_group].update(
            category.pk
            for category in partner.menu_categories.all()
            if category.pk in category_ids_by_slug.values()
        )

    return {
        group_slug: tuple(sorted(category_ids))
        for group_slug, category_ids in memberships.items()
    }


def equipment_group_for_category(category_id, memberships=None):
    """Return the equipment-group slug containing a live category."""
    memberships = memberships or equipment_group_category_ids()
    return next(
        (
            group_slug
            for group_slug, _, _ in EQUIPMENT_GROUPS
            if category_id in memberships.get(group_slug, ())
        ),
        "",
    )


def product_navigation_groups():
    """Build Equipment Group -> Manufacturer -> Category navigation."""
    categories = list(public_categories().order_by("display_order", "name"))
    category_by_id = {category.pk: category for category in categories}

    partners = (
        Partner.objects.filter(is_active=True)
        .exclude(equipment_group="")
        .prefetch_related("menu_categories")
        .order_by("equipment_group", "menu_order", "name")
    )
    partners_by_group = {group_slug: [] for group_slug, _, _ in EQUIPMENT_GROUPS}

    for partner in partners:
        brand_slug = slugify(partner.name)
        assigned_ids = {
            category.pk
            for category in partner.menu_categories.all()
            if category.pk in category_by_id
        }
        category_nodes = []
        for category in categories:
            if category.pk not in assigned_ids:
                continue

            # Manufacturer-owned catalogue categories (for example Eschweiler
            # ABG) expose their product groups, rather than repeating the
            # manufacturer's name as a generic child row.
            if (
                category.navigation_name.casefold()
                == partner.navigation_name.casefold()
            ):
                subcategories = list(category.subcategories.filter(
                    is_active=True,
                    parent__isnull=True,
                ).order_by("display_order", "name"))
                if subcategories:
                    category_nodes.extend({
                        "label": subcategory.name,
                        "url": subcategory.get_absolute_url(),
                    } for subcategory in subcategories)
                else:
                    category_nodes.extend({
                        "label": product.name,
                        "url": product.get_absolute_url(),
                    } for product in category.products.filter(
                        is_active=True,
                        brand__iexact=partner.name,
                    ).order_by("name"))
                continue

            category_nodes.append({
                "label": category.navigation_name,
                "url": category.get_absolute_url(),
            })

        manufacturer_node = {
            "partner": partner,
            "label": partner.navigation_name,
            "brand_slug": brand_slug,
            "categories": category_nodes,
            "direct_url": "",
        }

        # Medical-equipment catalogue families are sibling destinations: the
        # manufacturer overview and each assigned catalogue are deliberately
        # not rendered as a manufacturer accordion.
        if partner.equipment_group == "medical" and assigned_ids:
            manufacturer_node["categories"] = []
            # The generic manufacturer sibling is an overview destination.
            # Product cards belong exclusively to the assigned catalogue
            # sibling (for ZEISS, "ZEISS Light Microscopes").
            manufacturer_node["direct_url"] = (
                reverse("zeiss_microscopy")
                if partner.name.casefold() == "zeiss"
                else f"/partners/#partner-{brand_slug}"
            )
            # ZEISS exposes its active Light Microscopes catalogue here. The
            # separate ZEISS partner overview remains available on Partners,
            # but is not a Products & Solutions catalogue destination.
            if partner.name.casefold() != "zeiss":
                partners_by_group[partner.equipment_group].append(
                    manufacturer_node
                )
            for category in categories:
                if category.pk in assigned_ids:
                    partners_by_group[partner.equipment_group].append({
                        "partner": partner,
                        "label": category.name,
                        "brand_slug": brand_slug,
                        "categories": [],
                        "direct_url": category.get_absolute_url(),
                    })
            continue

        partners_by_group[partner.equipment_group].append(manufacturer_node)

    laboratory_items = []
    for label, destination_type, destination in LABORATORY_MENU_ITEMS:
        children = []
        if destination_type == "category":
            category = next(
                (item for item in categories if item.slug == destination),
                None,
            )
            if category is None:
                continue
            url = category.get_absolute_url()
            if destination in EXPANDABLE_LABORATORY_CATEGORIES:
                subcategories = list(category.subcategories.filter(
                    is_active=True,
                    parent__isnull=True,
                ).order_by("display_order", "name"))
                if subcategories:
                    children = [
                        {
                            "label": LABORATORY_CHILD_LABELS.get(
                                (destination, subcategory.slug),
                                subcategory.name,
                            ),
                            "url": subcategory.get_absolute_url(),
                        }
                        for subcategory in subcategories
                    ]
                else:
                    children = [
                        {
                            "label": product.name,
                            "url": product.get_absolute_url(),
                        }
                        for product in category.products.filter(
                            is_active=True,
                        ).order_by("name")
                    ]
        else:
            url = f"{reverse('product_list')}?brand={destination}"
        laboratory_items.append({
            "label": label,
            "url": url,
            "children": children,
            "control_id": f"laboratory-menu-{destination}",
        })

    return [
        {
            "slug": group_slug,
            "name": group_name,
            "heading_id": heading_id,
            "group_url": reverse(
                "equipment_group_products",
                args=[group_slug],
            ),
            "manufacturers": partners_by_group[group_slug],
            "flat_items": laboratory_items if group_slug == "laboratory" else [],
        }
        for group_slug, group_name, heading_id in EQUIPMENT_GROUPS
    ]
