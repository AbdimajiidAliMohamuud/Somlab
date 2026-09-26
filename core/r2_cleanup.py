import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from django.apps import apps
from django.conf import settings
from django.db import models


SCANNED_SOURCE_SUFFIXES = {
    ".css", ".env", ".html", ".js", ".json", ".md", ".py", ".toml",
    ".txt", ".yaml", ".yml",
}
EXCLUDED_SOURCE_PARTS = {
    ".git", ".venv", "__pycache__", "media", "node_modules",
    "r2_cleanup_reports", "staticfiles",
}
URL_RE = re.compile(r"(?:(?:https?:)?//)[^\s\"'<>]+", re.IGNORECASE)


def clean_object_key(value):
    """Return an R2 key in a stable slash-separated form."""
    return "/".join(part for part in str(value or "").replace("\\", "/").split("/") if part)


def normalize_reference(value, *, location, bucket_name, allowed_hosts):
    """Normalize one known file reference without accepting external URLs."""
    raw = str(value or "").strip().strip("\"'")
    if not raw:
        return None

    if raw.startswith(("http://", "https://", "//")):
        try:
            parsed = urlsplit(raw if not raw.startswith("//") else f"https:{raw}")
        except ValueError:
            return None
        if parsed.hostname and parsed.hostname.lower() not in allowed_hosts:
            return None
        raw = unquote(parsed.path)
    else:
        raw = unquote(raw.split("?", 1)[0].split("#", 1)[0])

    key = clean_object_key(raw)
    bucket_prefix = f"{bucket_name}/" if bucket_name else ""
    if bucket_prefix and key.startswith(bucket_prefix):
        key = key[len(bucket_prefix):]

    location = clean_object_key(location)
    if location and key != location and not key.startswith(f"{location}/"):
        key = f"{location}/{key}"
    return key or None


def r2_hosts(storage):
    options = settings.STORAGES.get("default", {}).get("OPTIONS", {})
    hosts = set()
    for value in (
        options.get("endpoint_url"),
        getattr(settings, "R2_PUBLIC_URL", ""),
        getattr(storage, "custom_domain", ""),
    ):
        if not value:
            continue
        parsed = urlsplit(value if "://" in value else f"https://{value}")
        if parsed.hostname:
            hosts.add(parsed.hostname.lower())
    return hosts


def _string_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, Path):
        yield str(value)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _string_values(key)
            yield from _string_values(item)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            yield from _string_values(item)


def _without_external_urls(text, allowed_hosts):
    def replace(match):
        raw = match.group(0)
        try:
            parsed = urlsplit(raw if not raw.startswith("//") else f"https:{raw}")
        except ValueError:
            # Unknown/malformed source text is retained so exact object-key
            # matching remains biased toward KEEP.
            return raw
        return raw if parsed.hostname and parsed.hostname.lower() in allowed_hosts else " "

    return URL_RE.sub(replace, text)


class ReferenceCollector:
    """Collect exact R2 object references with conservative source attribution."""

    def __init__(self, object_keys, *, location, bucket_name, allowed_hosts):
        self.object_keys = set(object_keys)
        self.location = clean_object_key(location)
        self.bucket_name = bucket_name
        self.allowed_hosts = {host.lower() for host in allowed_hosts}
        self.references = defaultdict(set)
        alias_to_keys = defaultdict(set)
        for key in self.object_keys:
            aliases = {key, f"/{key}"}
            if self.location and key.startswith(f"{self.location}/"):
                relative = key[len(self.location) + 1:]
                aliases.update({relative, f"/{relative}"})
            aliases.update(quote(alias, safe="/") for alias in tuple(aliases))
            for alias in aliases:
                if alias:
                    alias_to_keys[alias].add(key)
        self.alias_to_keys = alias_to_keys
        escaped = sorted((re.escape(alias) for alias in alias_to_keys), key=len, reverse=True)
        self.alias_pattern = re.compile("|".join(escaped)) if escaped else None

    def add_file_reference(self, value, source):
        key = normalize_reference(
            value,
            location=self.location,
            bucket_name=self.bucket_name,
            allowed_hosts=self.allowed_hosts,
        )
        if key in self.object_keys:
            self.references[key].add(source)

    def scan_text(self, value, source):
        if not self.alias_pattern:
            return
        for text in _string_values(value):
            safe_text = _without_external_urls(text, self.allowed_hosts)
            for match in self.alias_pattern.finditer(safe_text):
                for key in self.alias_to_keys[match.group(0)]:
                    self.references[key].add(source)

    @property
    def used_keys(self):
        return set(self.references)


def collect_website_references(collector, *, base_dir=None):
    """Scan database fields, settings, and application source for exact references."""
    text_field_types = (models.CharField, models.TextField, models.JSONField)
    file_field_types = (models.FileField,)

    for model in apps.get_models():
        concrete_fields = [field for field in model._meta.concrete_fields if not field.is_relation]
        for field in concrete_fields:
            source = f"database:{model._meta.label}.{field.name}"
            if isinstance(field, file_field_types):
                for value in model._default_manager.values_list(field.attname, flat=True).iterator():
                    if value:
                        collector.add_file_reference(value, source)
            elif isinstance(field, text_field_types):
                for value in model._default_manager.values_list(field.attname, flat=True).iterator():
                    if value:
                        collector.scan_text(value, source)

    for name in dir(settings):
        if name.startswith("_"):
            continue
        try:
            value = getattr(settings, name)
        except Exception:
            continue
        collector.scan_text(value, f"settings:{name}")

    root = Path(base_dir or settings.BASE_DIR)
    for path in root.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED_SOURCE_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in SCANNED_SOURCE_SUFFIXES and path.name != ".env":
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        collector.scan_text(content, f"source:{path.relative_to(root).as_posix()}")

    return collector.references


def format_bytes(size):
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1024


def manifest_payload(*, bucket, prefix, objects, generated_at):
    return {
        "version": 1,
        "generated_at": generated_at,
        "bucket": bucket,
        "managed_prefix": prefix,
        "unused_objects": [
            {
                "key": item["key"],
                "size": item["size"],
                "etag": item.get("etag", ""),
                "last_modified": item.get("last_modified", ""),
            }
            for item in objects
        ],
    }


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        json.dump(payload, output, indent=2, sort_keys=True)
        output.write("\n")
    return path
