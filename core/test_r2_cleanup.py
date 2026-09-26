import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from django.test import SimpleTestCase, TestCase

from catalog.models import Category, Product
from core.management.commands.cleanup_r2 import Command
from core.r2_cleanup import (
    ReferenceCollector,
    collect_website_references,
    normalize_reference,
)


class R2ReferenceNormalizationTests(SimpleTestCase):
    def test_normalizes_r2_urls_queries_bucket_paths_and_relative_keys(self):
        options = {
            "location": "media",
            "bucket_name": "somlab",
            "allowed_hosts": {"assets.example.com", "account.r2.cloudflarestorage.com"},
        }
        self.assertEqual(
            normalize_reference(
                "https://assets.example.com/media/products/Test%20Image.png?v=2#hero",
                **options,
            ),
            "media/products/Test Image.png",
        )
        self.assertEqual(
            normalize_reference("/somlab/media/products/item.webp?signature=x", **options),
            "media/products/item.webp",
        )
        self.assertEqual(
            normalize_reference("products/item.webp", **options),
            "media/products/item.webp",
        )

    def test_rejects_external_urls_even_when_their_path_matches_an_r2_key(self):
        self.assertIsNone(normalize_reference(
            "https://external.example/media/products/item.webp",
            location="media",
            bucket_name="somlab",
            allowed_hosts={"assets.example.com"},
        ))
        self.assertIsNone(normalize_reference(
            "https://[malformed/media/products/item.webp",
            location="media",
            bucket_name="somlab",
            allowed_hosts={"assets.example.com"},
        ))

    def test_text_scan_matches_exact_r2_references_but_ignores_external_urls(self):
        collector = ReferenceCollector(
            {"media/products/used.png", "media/products/external.png"},
            location="media",
            bucket_name="somlab",
            allowed_hosts={"assets.example.com"},
        )
        collector.scan_text(
            '<img src="https://assets.example.com/media/products/used.png?width=800"> '
            '<img src="https://external.example/media/products/external.png">',
            "rich-text",
        )
        self.assertEqual(collector.used_keys, {"media/products/used.png"})


class R2DatabaseReferenceTests(TestCase):
    def test_scans_file_fields_and_text_content_across_installed_models(self):
        product = Product.objects.create(
            category=Category.objects.get(slug="chemistry"),
            name="R2 reference test",
            slug="r2-reference-test",
            product_code="R2-REF-TEST",
            short_description="Reference scanner test.",
            description=(
                '<img src="https://assets.example.com/media/content/rich-image.png?x=1">'
                '<img src="https://external.example/media/content/external-image.png">'
            ),
            image="products/database-image.png",
        )
        collector = ReferenceCollector(
            {
                "media/products/database-image.png",
                "media/content/rich-image.png",
                "media/content/external-image.png",
            },
            location="media",
            bucket_name="somlab",
            allowed_hosts={"assets.example.com"},
        )
        with TemporaryDirectory() as source_root:
            collect_website_references(collector, base_dir=source_root)

        self.assertIn("media/products/database-image.png", collector.used_keys)
        self.assertIn("media/content/rich-image.png", collector.used_keys)
        self.assertNotIn("media/content/external-image.png", collector.used_keys)
        product.delete()


class R2DeletionSafetyTests(SimpleTestCase):
    def test_verify_manifest_rechecks_metadata_and_writes_only_safe_candidates(self):
        command = Command()
        modified = datetime(2026, 8, 21, 12, 0, 0, 367000, tzinfo=timezone.utc)
        head_modified = modified.replace(microsecond=0)
        client = Mock()
        client.head_object.return_value = {
            "ContentLength": 10,
            "ETag": '"etag-a"',
            "LastModified": head_modified,
        }
        current = {
            "media/unused-a.png": {
                "key": "media/unused-a.png",
                "normalized_key": "media/unused-a.png",
                "size": 10,
                "etag": "etag-a",
                "last_modified": modified.isoformat(),
            },
            "media/now-active.png": {
                "key": "media/now-active.png",
                "normalized_key": "media/now-active.png",
                "size": 20,
                "etag": "etag-b",
                "last_modified": modified.isoformat(),
            },
        }
        manifest = {
            "version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "bucket": "somlab",
            "managed_prefix": "media/",
            "unused_objects": [
                {key: value for key, value in item.items() if key != "normalized_key"}
                for item in current.values()
            ],
        }

        with TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir, "reviewed.json")
            verified_path = Path(temp_dir, "verified.json")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            command._verify_manifest(
                client=client,
                bucket="somlab",
                prefix="media/",
                current_objects=current,
                current_unused={"media/unused-a.png"},
                manifest_path=manifest_path,
                verified_manifest_path=verified_path,
            )
            verified = json.loads(verified_path.read_text(encoding="utf-8"))

        self.assertEqual(
            [item["key"] for item in verified["unused_objects"]],
            ["media/unused-a.png"],
        )
        self.assertEqual(
            verified["unused_objects"][0]["normalized_reference_count"], 0
        )
        self.assertEqual(len(verified["verification"]["skipped_objects"]), 1)
        client.delete_object.assert_not_called()

    def test_delete_uses_reviewed_manifest_and_skips_objects_no_longer_unused(self):
        command = Command()
        client = Mock()
        client.head_object.return_value = {"ContentLength": 10, "ETag": '"etag-a"'}
        current = {
            "media/unused-a.png": {
                "key": "media/unused-a.png", "normalized_key": "media/unused-a.png",
                "size": 10, "etag": "etag-a",
            },
            "media/now-active.png": {
                "key": "media/now-active.png", "normalized_key": "media/now-active.png",
                "size": 20, "etag": "etag-b",
            },
        }
        manifest = {
            "version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "bucket": "somlab",
            "managed_prefix": "media/",
            "unused_objects": list(current.values()),
        }

        with TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir, "reviewed.json")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            command._delete_from_manifest(
                client=client,
                bucket="somlab",
                prefix="media/",
                current_objects=current,
                current_unused={"media/unused-a.png"},
                manifest_path=manifest_path,
                confirmation="DELETE-UNUSED-R2",
                log_file=None,
            )
            log_lines = manifest_path.with_suffix(".deletions.jsonl").read_text().splitlines()

        client.delete_object.assert_called_once_with(
            Bucket="somlab", Key="media/unused-a.png"
        )
        self.assertEqual(len(log_lines), 1)
        self.assertEqual(json.loads(log_lines[0])["key"], "media/unused-a.png")
