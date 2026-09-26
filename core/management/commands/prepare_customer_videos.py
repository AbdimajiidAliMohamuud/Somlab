from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.customer_video import save_video_media
from core.models import CustomerProjectMedia


class Command(BaseCommand):
    help = "Create playback assets for selected existing customer videos; retain originals."

    def add_arguments(self, parser):
        parser.add_argument("media_ids", type=int, nargs="+")

    def handle(self, *args, **options):
        for pk in options["media_ids"]:
            media = CustomerProjectMedia.objects.get(pk=pk, media_type="video")
            if media.playback_file and media.video_poster:
                self.stdout.write(f"Video {pk}: playback assets already exist.")
                continue
            if not media.file:
                raise CommandError(f"Video {pk} has no uploaded file.")
            with media.file.open("rb") as source, transaction.atomic():
                save_video_media(media, source, replace_original=False)
            self.stdout.write(self.style.SUCCESS(f"Video {pk}: playback and poster saved; original retained."))
