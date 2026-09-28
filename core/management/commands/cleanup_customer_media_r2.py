"""Conservative, customer-project-only R2 orphan audit."""

from datetime import timedelta

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.customer_media_lifecycle import (
    CUSTOMER_MEDIA_PREFIX, is_file_referenced, is_managed_customer_media_name,
)
from core.r2_cleanup import (
    ReferenceCollector, clean_object_key, collect_website_references, r2_hosts,
)


class Command(BaseCommand):
    help = (
        "Audit orphan customer project uploads in R2 (dry-run by default). "
        "Pass --delete to remove only old, still-unreferenced objects."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete", action="store_true",
            help="Delete eligible orphan customer project objects after rechecking them.",
        )
        parser.add_argument(
            "--min-age-hours", type=int, default=24,
            help="Protect recently uploaded objects (default: 24 hours).",
        )

    def handle(self, *args, **options):
        if options["min_age_hours"] < 1:
            raise CommandError("--min-age-hours must be at least 1.")
        storage, client, bucket, prefix = self._r2_context()
        cutoff = timezone.now() - timedelta(hours=options["min_age_hours"])
        objects = self._list_customer_objects(client, bucket, prefix)
        keys = {item["key"] for item in objects}
        collector = ReferenceCollector(
            keys,
            location=storage.location,
            bucket_name=bucket,
            allowed_hosts=r2_hosts(storage),
        )
        collect_website_references(collector)
        candidates = [
            item for item in objects
            if item["key"] not in collector.used_keys
            and item["modified"] <= cutoff
        ]
        self.stdout.write(
            f"Customer project objects: {len(objects)}; eligible orphans: {len(candidates)} "
            f"(minimum age: {options['min_age_hours']} hours)."
        )
        for item in candidates:
            self.stdout.write(f"  {item['key']} ({item['size']} bytes)")
        if not options["delete"]:
            self.stdout.write("Dry run only. No R2 objects deleted; pass --delete to remove eligible orphans.")
            return

        # Re-scan references after the report, then re-check each key and its
        # R2 identity immediately before deletion. A concurrent upload is kept.
        fresh = ReferenceCollector(
            {item["key"] for item in candidates},
            location=storage.location,
            bucket_name=bucket,
            allowed_hosts=r2_hosts(storage),
        )
        collect_website_references(fresh)
        deleted = skipped = 0
        for item in candidates:
            key = item["key"]
            relative_name = key[len(clean_object_key(storage.location)) + 1:]
            if key in fresh.used_keys or is_file_referenced(relative_name):
                skipped += 1
                continue
            try:
                head = client.head_object(Bucket=bucket, Key=key)
                if (
                    int(head.get("ContentLength", -1)) != item["size"]
                    or str(head.get("ETag", "")).strip('"') != item["etag"]
                    or head.get("LastModified") is None
                    or head["LastModified"] > cutoff
                ):
                    skipped += 1
                    continue
                client.delete_object(Bucket=bucket, Key=key)
            except Exception as error:
                raise CommandError(f"R2 deletion stopped at {key}: {error}") from error
            deleted += 1
            self.stdout.write(self.style.SUCCESS(f"DELETED {key}"))
        self.stdout.write(f"Deleted {deleted}; skipped {skipped} changed or referenced objects.")

    @staticmethod
    def _r2_context():
        backend = settings.STORAGES.get("default", {}).get("BACKEND", "")
        if not settings.R2_ENABLED or "storages.backends.s3" not in backend:
            raise CommandError("Customer R2 cleanup requires the configured R2 storage.")
        storage = default_storage
        location = clean_object_key(getattr(storage, "location", ""))
        client = getattr(getattr(getattr(storage, "connection", None), "meta", None), "client", None)
        bucket = getattr(storage, "bucket_name", "")
        if not location or client is None or not bucket:
            raise CommandError("Customer R2 cleanup requires a bucket, location, and client.")
        return storage, client, bucket, f"{location}/{CUSTOMER_MEDIA_PREFIX}"

    @staticmethod
    def _list_customer_objects(client, bucket, prefix):
        objects = []
        location = prefix.removesuffix(CUSTOMER_MEDIA_PREFIX)
        for page in client.get_paginator("list_objects_v2").paginate(
            Bucket=bucket, Prefix=prefix,
        ):
            for item in page.get("Contents", []):
                key = str(item["Key"])
                relative_name = key.removeprefix(location)
                modified = item.get("LastModified")
                if (
                    not key.startswith(prefix)
                    or not is_managed_customer_media_name(relative_name)
                    or modified is None
                ):
                    continue
                objects.append({
                    "key": key,
                    "size": int(item.get("Size", 0)),
                    "etag": str(item.get("ETag", "")).strip('"'),
                    "modified": modified,
                })
        return sorted(objects, key=lambda item: item["key"])
