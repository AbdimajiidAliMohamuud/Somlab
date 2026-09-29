from .models import Customer


def normalize_customer_display_order(*, using=None):
    """Keep the customer admin order contiguous without changing relative order."""
    customers = list(
        Customer.objects.using(using).select_for_update().order_by("display_order", "pk")
    )
    for index, customer in enumerate(customers):
        if customer.display_order != index:
            Customer.objects.using(using).filter(pk=customer.pk).update(
                display_order=index
            )
    return len(customers)
