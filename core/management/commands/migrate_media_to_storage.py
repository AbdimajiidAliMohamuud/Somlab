from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Copy files from the local media directory into the configured default storage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Delete an existing destination object before uploading it again.",
        )

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        if not media_root.exists():
            self.stdout.write(self.style.WARNING("The local media directory does not exist."))
            return

        copied = skipped = failed = 0
        for source in sorted(media_root.rglob("*")):
            if not source.is_file() or source.name.startswith("."):
                continue

            object_name = source.relative_to(media_root).as_posix()
            try:
                if default_storage.exists(object_name):
                    if not options["overwrite"]:
                        skipped += 1
                        self.stdout.write(f"Skipped existing: {object_name}")
                        continue
                    default_storage.delete(object_name)

                with source.open("rb") as source_file:
                    saved_name = default_storage.save(object_name, File(source_file))
                copied += 1
                self.stdout.write(self.style.SUCCESS(f"Uploaded: {saved_name}"))
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"Failed: {object_name} ({exc})"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Media migration complete: {copied} uploaded, "
                f"{skipped} skipped, {failed} failed."
            )
        )
        if failed:
            raise SystemExit(1)
