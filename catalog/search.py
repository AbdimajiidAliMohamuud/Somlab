from django.db.models import Q, QuerySet

from .models import Product
from .scope import public_products


def search_public_products(
    query: str,
    *,
    queryset: QuerySet[Product] | None = None,
) -> QuerySet[Product]:
    """Apply the public catalogue's shared product-search rules."""
    products = queryset if queryset is not None else public_products()
    normalized_query = query.strip()
    if not normalized_query:
        return products

    return products.filter(
        Q(name__icontains=normalized_query)
        | Q(brand__icontains=normalized_query)
        | Q(category__name__icontains=normalized_query)
        | Q(subcategory__name__icontains=normalized_query)
        | Q(product_code__icontains=normalized_query)
        | Q(short_description__icontains=normalized_query)
    )
