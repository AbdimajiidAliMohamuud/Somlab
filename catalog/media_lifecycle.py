"""Delete obsolete product-gallery objects only after a successful DB commit."""

from django.db import transaction

from core.customer_media_lifecycle import is_file_referenced


def schedule_product_gallery_cleanup(storage, name):
    if (
        not name.startswith("products/gallery/")
        or "\\" in name
        or any(part in {"", ".", ".."} for part in name.split("/"))
    ):
        return

    def cleanup():
        if not is_file_referenced(name):
            storage.delete(name)

    transaction.on_commit(cleanup, robust=True)
