import hashlib
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Customer, CustomerProject, CustomerProjectMedia


CUSTOMER_SLUG = "shaafi-hospital"
PROJECT_TITLE = "Laboratory equipment delivery"
MEDIA = (
    ("DSC09301.JPG", "Beckman Coulter Access 2 laboratory system"),
    ("DSC09302.JPG", "Beckman Coulter Access 2 laboratory system"),
    ("DSC09304.JPG", "Beckman Coulter Access 2 workstation"),
    ("DSC09305.JPG", "Beckman Coulter Access 2 laboratory system"),
    ("DSC09306.JPG", "Beckman Coulter Access 2 laboratory system"),
    ("DSC09307.JPG", "Beckman Coulter Access 2 laboratory system"),
    ("DSC09308.JPG", "BIOBASE -40°C freezer"),
    ("DSC09309.JPG", "BIOBASE -40°C freezer"),
    ("DSC09310.JPG", "BIOBASE blood storage refrigerator"),
    ("DSC09311.JPG", "BIOBASE blood storage refrigerator"),
    ("DSC09312.JPG", "BIOBASE laboratory refrigerators"),
    ("DSC09313.JPG", "BIOBASE laboratory equipment"),
    ("DSC09314.JPG", "BIOBASE laboratory equipment"),
    ("DSC09316.JPG", "BIOBASE blood collection monitor"),
    ("DSC09317.JPG", "BIOBASE blood thaw machine"),
    ("DSC09319.JPG", "Laboratory equipment at Shaafi Hospital"),
    ("DSC09320.JPG", "Laboratory equipment at Shaafi Hospital"),
    ("DSC09322.JPG", "BIOBASE laboratory equipment"),
    ("DSC09323.JPG", "BIOBASE laboratory equipment"),
    ("DSC09325.JPG", "BIOBASE laboratory equipment"),
    ("DSC09326.JPG", "Laboratory centrifuges at Shaafi Hospital"),
    ("DSC09327.JPG", "Laboratory centrifuges at Shaafi Hospital"),
    ("DSC09328.JPG", "Laboratory centrifuges at Shaafi Hospital"),
    ("DSC09329.JPG", "Laboratory centrifuges at Shaafi Hospital"),
    ("DSC09330.JPG", "Laboratory equipment at Shaafi Hospital"),
    ("DSC09331.JPG", "Laboratory equipment at Shaafi Hospital"),
    ("DSC09332.JPG", "Laboratory equipment at Shaafi Hospital"),
)


class Command(BaseCommand):
    help = "Import Shaafi Hospital portfolio media using the configured media storage."

    def add_arguments(self, parser):
        parser.add_argument("source_directory", type=Path)

    def handle(self, *args, **options):
        source_directory = options["source_directory"].expanduser().resolve()
        if not source_directory.is_dir():
            raise CommandError(f"Source directory does not exist: {source_directory}")

        missing = [name for name, _caption in MEDIA if not (source_directory / name).is_file()]
        if missing:
            raise CommandError("Missing source files: " + ", ".join(missing))

        try:
            customer = Customer.objects.get(slug=CUSTOMER_SLUG)
        except Customer.DoesNotExist as exc:
            raise CommandError(f"Customer not found: {CUSTOMER_SLUG}") from exc

        stored_media = []
        stored = reused = 0
        for order, (filename, caption) in enumerate(MEDIA):
            source_path = source_directory / filename
            digest = self._sha256(source_path)
            storage_name = (
                f"customers/projects/{CUSTOMER_SLUG}/{digest[:12]}-{filename}"
            )
            if default_storage.exists(storage_name):
                reused += 1
            else:
                with source_path.open("rb") as source_file:
                    saved_name = default_storage.save(storage_name, File(source_file))
                if saved_name != storage_name:
                    raise CommandError(
                        f"Storage changed the requested object key to {saved_name}."
                    )
                stored += 1
            stored_media.append((order, storage_name, caption))

        with transaction.atomic():
            project, _created = CustomerProject.objects.get_or_create(
                customer=customer,
                title=PROJECT_TITLE,
                defaults={
                    "work_type": "supply",
                    "description": "",
                    "date": None,
                    "display_order": 0,
                },
            )
            changed_fields = []
            expected_values = {
                "work_type": "supply",
                "description": "",
                "date": None,
                "display_order": 0,
            }
            for field, value in expected_values.items():
                if getattr(project, field) != value:
                    setattr(project, field, value)
                    changed_fields.append(field)
            if changed_fields:
                project.save(update_fields=changed_fields)

            for order, storage_name, caption in stored_media:
                CustomerProjectMedia.objects.update_or_create(
                    project=project,
                    display_order=order,
                    defaults={
                        "media_type": "image",
                        "file": storage_name,
                        "video_url": "",
                        "caption": caption,
                        "description": "",
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Shaafi Hospital portfolio complete: "
                f"{len(stored_media)} photographs linked; "
                f"{stored} stored, {reused} reused."
            )
        )

    @staticmethod
    def _sha256(path):
        digest = hashlib.sha256()
        with path.open("rb") as source_file:
            for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
