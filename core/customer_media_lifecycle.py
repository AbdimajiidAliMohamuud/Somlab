"""Safe storage cleanup and ordering for customer project media only."""

from urllib.parse import quote

from django.apps import apps
from django.db import models, transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import CustomerProject, CustomerProjectMedia


CUSTOMER_MEDIA_PREFIX = "customers/projects/"
MEDIA_FILE_FIELDS = ("file", "playback_file", "video_poster")


def is_managed_customer_media_name(name):
    """Never delete static, shared, absolute, or traversal paths."""
    return (
        isinstance(name, str)
        and name.startswith(CUSTOMER_MEDIA_PREFIX)
        and "\\" not in name
        and all(part not in {"", ".", ".."} for part in name.split("/"))
    )


def is_file_referenced(name, *, using=None):
    """Check file fields and text links across installed models."""
    text_aliases = {name, quote(name, safe="/")}
    for model in apps.get_models():
        for field in model._meta.concrete_fields:
            if isinstance(field, models.FileField):
                if model._base_manager.using(using or "default").filter(
                    **{field.attname: name}
                ).exists():
                    return True
            elif isinstance(field, (models.CharField, models.TextField)):
                for alias in text_aliases:
                    if model._base_manager.using(using or "default").filter(
                        **{f"{field.attname}__contains": alias}
                    ).exists():
                        return True
    return False


def delete_unreferenced_file(storage, name, *, using=None):
    if is_managed_customer_media_name(name) and not is_file_referenced(name, using=using):
        storage.delete(name)


def schedule_unreferenced_file_cleanup(storage, name, *, using=None):
    if is_managed_customer_media_name(name):
        transaction.on_commit(
            lambda: delete_unreferenced_file(storage, name, using=using),
            using=using,
            robust=True,
        )


def normalize_customer_media_order(project_id, *, using=None):
    database = using or "default"
    if not CustomerProject.objects.using(database).filter(pk=project_id).exists():
        return
    items = list(CustomerProjectMedia.objects.using(database).filter(
        project_id=project_id,
    ).order_by("display_order", "pk"))
    changed = []
    for index, item in enumerate(items):
        if item.display_order != index:
            item.display_order = index
            changed.append(item)
    if changed:
        CustomerProjectMedia.objects.using(database).bulk_update(changed, ["display_order"])


def move_customer_media_to_index(media, index):
    """Place an admin-edited item at its requested position, closing all gaps."""
    database = media._state.db or "default"
    items = list(CustomerProjectMedia.objects.using(database).filter(
        project_id=media.project_id,
    ).exclude(pk=media.pk).order_by("display_order", "pk"))
    items.insert(max(0, min(index, len(items))), media)
    changed = []
    for position, item in enumerate(items):
        if item.display_order != position:
            item.display_order = position
            changed.append(item)
    if changed:
        CustomerProjectMedia.objects.using(database).bulk_update(changed, ["display_order"])


@receiver(pre_save, sender=CustomerProjectMedia)
def remember_replaced_customer_media(sender, instance, using, **kwargs):
    instance._previous_media_files = None
    if instance.pk:
        instance._previous_media_files = sender.objects.using(using).filter(
            pk=instance.pk,
        ).values(*MEDIA_FILE_FIELDS).first()


@receiver(post_save, sender=CustomerProjectMedia)
def cleanup_replaced_customer_media(sender, instance, using, **kwargs):
    previous = getattr(instance, "_previous_media_files", None) or {}
    for field_name in MEDIA_FILE_FIELDS:
        old_name = previous.get(field_name)
        new_name = getattr(instance, field_name).name
        if old_name and old_name != new_name:
            storage = sender._meta.get_field(field_name).storage
            schedule_unreferenced_file_cleanup(storage, old_name, using=using)
    instance._previous_media_files = None


@receiver(post_delete, sender=CustomerProjectMedia)
def cleanup_deleted_customer_media(sender, instance, using, **kwargs):
    for field_name in MEDIA_FILE_FIELDS:
        field = getattr(instance, field_name)
        if field.name:
            schedule_unreferenced_file_cleanup(field.storage, field.name, using=using)
    transaction.on_commit(
        lambda: normalize_customer_media_order(instance.project_id, using=using),
        using=using,
        robust=True,
    )
