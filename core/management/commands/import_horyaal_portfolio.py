import hashlib
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Customer, CustomerProject, CustomerProjectMedia


CUSTOMER_SLUG = "horyaal-hospital"
PROJECT_TITLE = "Laboratory equipment delivery"
MEDIA = (
    ("DSC09237.JPG", "Beckman Coulter AU480 chemistry analyzer"),
    ("DSC09236.JPG", "Beckman Coulter AU480 chemistry analyzer"),
    ("DSC09242.JPG", "Beckman Coulter AU480 chemistry analyzer"),
    ("DSC09239.JPG", "Beckman Coulter AU480 workstation"),
    ("DSC09233.JPG", "Laboratory analyzer workstation"),
    ("DSC09245.JPG", "Beckman Coulter Access 2 laboratory system"),
    ("DSC09246.JPG", "Beckman Coulter Access 2 laboratory system"),
    ("DSC09247.JPG", "Beckman Coulter Access 2 laboratory system"),
    ("DSC09252.JPG", "Beckman Coulter DxH 560 hematology analyzer"),
    ("DSC09253.JPG", "Beckman Coulter DxH 560 hematology analyzer"),
    ("DSC09255.JPG", "Molbio Truelab Duo and Trueprep AUTO v2 systems"),
    ("DSC09258.JPG", "Molbio Truelab Duo and Trueprep AUTO v2 systems"),
    ("DSC09259.JPG", "Molbio Truelab Duo and Trueprep AUTO v2 systems"),
    ("DSC09261.JPG", "Molbio Truelab Duo and Trueprep AUTO v2 systems"),
    ("DSC09262.JPG", "Molbio Truelab system"),
    ("DSC09263.JPG", "Eschweiler combi line blood gas analyzer"),
    ("DSC09264.JPG", "Eschweiler combi line blood gas analyzer"),
    ("DSC09265.JPG", "Eschweiler combi line blood gas analyzer"),
    ("DSC09266.JPG", "Eschweiler combi line blood gas analyzer"),
    ("DSC09267.JPG", "Eschweiler combi line blood gas analyzer"),
    ("DSC09269.JPG", "Beckman Coulter MicroScan autoSCAN-4 system"),
    ("DSC09270.JPG", "Beckman Coulter MicroScan autoSCAN-4 system"),
    ("DSC09272.JPG", "Beckman Coulter MicroScan autoSCAN-4 system"),
    ("DSC09274.JPG", "Beckman Coulter MicroScan autoSCAN-4 system"),
    ("DSC09275.JPG", "Laboratory testing workstation in use"),
    ("DSC09276.JPG", "Laboratory testing workstation in use"),
    ("DSC09277.JPG", "Laboratory results workstation"),
    ("DSC09279.JPG", "Laboratory results workstation"),
)


class Command(BaseCommand):
    help = "Import the verified Horyaal Hospital project photographs."

    def add_arguments(self, parser):
        parser.add_argument(
            "source_directory",
            type=Path,
            help="Directory containing the original Horyaal project photographs.",
        )

    def handle(self, *args, **options):
        source_directory = options["source_directory"].expanduser().resolve()
        if not source_directory.is_dir():
            raise CommandError(f"Source directory does not exist: {source_directory}")

        sources = []
        for filename, caption in MEDIA:
            source = source_directory / filename
            if not source.is_file():
                raise CommandError(f"Missing Horyaal project asset: {filename}")
            sources.append((source, caption, self._sha256(source)))

        customer = Customer.objects.filter(slug=CUSTOMER_SLUG).first()
        if customer is None:
            raise CommandError("Horyaal Hospital customer record was not found.")

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
            "Horyaal Hospital portfolio complete: "
            f"{len(sources)} photographs linked; {stored} stored, {reused} reused."
        ))

    @staticmethod
    def _sha256(path):
        digest = hashlib.sha256()
        with path.open("rb") as source_file:
            for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
