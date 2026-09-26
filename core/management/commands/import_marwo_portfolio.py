import hashlib
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Customer, CustomerProject, CustomerProjectMedia


CUSTOMER_SLUG = "marwo-fertility-center"
PROJECT_TITLE = "Laboratory equipment delivery"
MEDIA = (
    ("DSC09283.JPG", "Laboratory equipment at Marwo Fertility Center"),
    ("DSC09281.JPG", "Beckman Coulter Access 2 laboratory system"),
    ("DSC09282.JPG", "Beckman Coulter Access 2 laboratory system"),
    ("DSC09284.JPG", "Beckman Coulter Access 2 laboratory system"),
    ("DSC09285.JPG", "Beckman Coulter Access 2 workstation"),
    ("DSC09287.JPG", "Beckman Coulter Access 2 laboratory system"),
    ("DSC09288.JPG", "Beckman Coulter DxH 560 hematology analyzer"),
    ("DSC09290.JPG", "Beckman Coulter DxH 560 hematology analyzer"),
    ("DSC09291.JPG", "Beckman Coulter DxH 560 hematology analyzer"),
    ("DSC09293.JPG", "Beckman Coulter DxH 560 hematology analyzer"),
    ("DSC09299.JPG", "Beckman Coulter DxH 560 hematology analyzer"),
)


class Command(BaseCommand):
    help = "Import the verified Marwo Fertility Center project photographs."

    def add_arguments(self, parser):
        parser.add_argument(
            "source_directory",
            type=Path,
            help="Directory containing the original Marwo project photographs.",
        )

    def handle(self, *args, **options):
        source_directory = options["source_directory"].expanduser().resolve()
        if not source_directory.is_dir():
            raise CommandError(f"Source directory does not exist: {source_directory}")

        sources = []
        for filename, caption in MEDIA:
            source = source_directory / filename
            if not source.is_file():
                raise CommandError(f"Missing Marwo project asset: {filename}")
            sources.append((source, caption, self._sha256(source)))

        customer = Customer.objects.filter(slug=CUSTOMER_SLUG).first()
        if customer is None:
            raise CommandError("Marwo Fertility Center customer record was not found.")

        stored = reused = 0
        with transaction.atomic():
            project, _ = CustomerProject.objects.get_or_create(
                customer=customer,
                title=PROJECT_TITLE,
                defaults={
                    "work_type": "supply",
                    "description": "",
                    "date": None,
                    "display_order": 0,
                },
            )
            for display_order, (source, caption, content_hash) in enumerate(sources):
                storage_name = (
                    f"customers/projects/{CUSTOMER_SLUG}/"
                    f"{content_hash[:12]}-{source.name}"
                )
                if default_storage.exists(storage_name):
                    reused += 1
                else:
                    with source.open("rb") as source_file:
                        saved_name = default_storage.save(storage_name, File(source_file))
                    if saved_name != storage_name:
                        raise CommandError(
                            f"Storage changed the requested object key to {saved_name}."
                        )
                    stored += 1

                CustomerProjectMedia.objects.update_or_create(
                    project=project,
                    display_order=display_order,
                    defaults={
                        "file": storage_name,
                        "media_type": "image",
                        "video_url": "",
                        "caption": caption,
                        "description": "",
                    },
                )

        self.stdout.write(self.style.SUCCESS(
            "Marwo Fertility Center portfolio complete: "
            f"{len(sources)} photographs linked; {stored} stored, {reused} reused."
        ))

    @staticmethod
    def _sha256(path):
        digest = hashlib.sha256()
        with path.open("rb") as source_file:
            for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
