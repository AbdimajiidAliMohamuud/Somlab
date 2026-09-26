import hashlib
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Customer, CustomerProject, CustomerProjectMedia


CUSTOMER_SLUG = "mogadishu-specialist-hospital"
PROJECT_TITLE = "Laboratory equipment delivery"
REMOVED_DUPLICATE_FILENAMES = {"DSC09361.JPG"}
MEDIA = (
    ("DSC09349.JPG", "Laboratory analyzer workstation"),
    ("DSC09350.JPG", "Laboratory analyzer operation"),
    ("DSC09351.JPG", "Laboratory team member"),
    ("DSC09352.JPG", "Beckman Coulter DxC 500i laboratory system"),
    ("DSC09353.JPG", "Beckman Coulter DxC 500i laboratory system"),
    ("DSC09354.JPG", "Beckman Coulter DxC 500i laboratory system"),
    ("DSC09356.JPG", "Beckman Coulter DxC 500i laboratory system"),
    ("DSC09357.JPG", "Beckman Coulter DxC 500i laboratory system"),
    ("DSC09358.JPG", "Beckman Coulter DxC 500i laboratory system"),
    ("DSC09360.JPG", "Beckman Coulter DxC 500i laboratory system"),
    ("DSC09363.JPG", "Laboratory analyzer operation"),
    ("DSC09364.JPG", "Laboratory analyzer operation"),
    ("DSC09365.JPG", "Laboratory analyzer operation"),
    ("DSC09366.JPG", "Laboratory analyzer operation"),
    ("DSC09368.JPG", "Laboratory team member"),
    ("DSC09370.JPG", "Beckman Coulter MicroScan autoSCAN-4 system"),
    ("DSC09371.JPG", "Beckman Coulter MicroScan autoSCAN-4 system"),
    ("DSC09373.JPG", "Beckman Coulter MicroScan autoSCAN-4 system"),
    ("DSC09374.JPG", "Beckman Coulter MicroScan autoSCAN-4 system"),
    ("DSC09377.JPG", "Beckman Coulter MicroScan autoSCAN-4 system"),
    ("DSC09378.JPG", "PowerVar 2.0 laboratory equipment"),
    ("DSC09379.JPG", "Laboratory testing workstation"),
)


class Command(BaseCommand):
    help = "Import the verified Mogadishu Specialist Hospital project photographs."

    def add_arguments(self, parser):
        parser.add_argument(
            "source_directory",
            type=Path,
            help="Directory containing the original Mogadishu Specialist Hospital photographs.",
        )

    def handle(self, *args, **options):
        source_directory = options["source_directory"].expanduser().resolve()
        if not source_directory.is_dir():
            raise CommandError(f"Source directory does not exist: {source_directory}")

        sources = []
        for filename, caption in MEDIA:
            source = source_directory / filename
            if not source.is_file():
                raise CommandError(f"Missing Mogadishu Specialist Hospital asset: {filename}")
            sources.append((source, caption, self._sha256(source)))

        customer = Customer.objects.filter(slug=CUSTOMER_SLUG).first()
        if customer is None:
            raise CommandError("Mogadishu Specialist Hospital customer record was not found.")

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
                    file=storage_name,
                    defaults={
                        "display_order": display_order,
                        "media_type": "image",
                        "video_url": "",
                        "caption": caption,
                        "description": "",
                    },
                )

            for media in project.media.all():
                if any(
                    media.file.name.endswith(filename)
                    for filename in REMOVED_DUPLICATE_FILENAMES
                ):
                    media.delete()

        self.stdout.write(self.style.SUCCESS(
            "Mogadishu Specialist Hospital portfolio complete: "
            f"{len(sources)} photographs linked; {stored} stored, {reused} reused."
        ))

    @staticmethod
    def _sha256(path):
        digest = hashlib.sha256()
        with path.open("rb") as source_file:
            for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
