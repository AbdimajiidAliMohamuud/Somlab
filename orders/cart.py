from decimal import Decimal
from catalog.scope import public_products


def _parse_cart_key(key):
    product_part, separator, variant_part = str(key).partition(":")
    try:
        product_id = int(product_part)
        variant_id = int(variant_part) if separator and variant_part else None
    except (TypeError, ValueError):
        return None, None
    return product_id, variant_id


def get_cart_items(request):
    cart = request.session.get("cart", {})
    parsed_lines = []
    for line_key, quantity in cart.items():
        product_id, variant_id = _parse_cart_key(line_key)
        if product_id is not None:
            parsed_lines.append((str(line_key), product_id, variant_id, quantity))

    products = {
        product.id: product
        for product in public_products()
        .filter(id__in=[line[1] for line in parsed_lines])
        .select_related("category")
        .prefetch_related("variants")
    }
    items = []
    total = Decimal("0")
    for line_key, product_id, variant_id, raw_quantity in parsed_lines:
        product = products.get(product_id)
        if not product:
            continue
        variant = None
        if variant_id is not None:
            variant = next(
                (item for item in product.variants.all() if item.id == variant_id),
                None,
            )
            if not variant:
                continue
        try:
            quantity = max(1, min(999, int(raw_quantity)))
        except (TypeError, ValueError):
            quantity = 1
        subtotal = product.effective_price * quantity
        total += subtotal
        items.append({
            "line_key": line_key,
            "product": product,
            "variant": variant,
            "quantity": quantity,
            "subtotal": subtotal,
        })
    return items, total
