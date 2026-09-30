"""Customer-only video validation and browser playback assets."""
from contextlib import contextmanager
import logging
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File


logger = logging.getLogger(__name__)

# Decimal GB, exclusive: keep both the server and form at exactly the same limit.
MAX_VIDEO_BYTES = 1_000_000_000 - 1
VIDEO_LIMIT_MESSAGE = "Each video must be under 1 GB (maximum 999,999,999 bytes)."
VIDEO_MIME_TYPES = {
    "mp4": "video/mp4", "m4v": "video/mp4", "mov": "video/quicktime",
    "webm": "video/webm", "ogv": "video/ogg", "ogg": "video/ogg",
}


def validate_video_upload(upload):
    extension = Path(upload.name).suffix.lower().lstrip(".")
    if extension not in VIDEO_MIME_TYPES:
        raise ValidationError("Upload an MP4, WebM, MOV, M4V, or Ogg video.")
    if upload.size > MAX_VIDEO_BYTES:
        raise ValidationError(VIDEO_LIMIT_MESSAGE)
    if not upload.size:
        raise ValidationError("The video is empty. Choose a playable video file.")
    upload.seek(0)
    signature = upload.read(32)
    upload.seek(0)
    valid = (
        signature[4:8] in {b"ftyp", b"moov", b"mdat", b"wide", b"free"}
        if extension in {"mp4", "m4v", "mov"}
        else signature.startswith(b"\x1aE\xdf\xa3") if extension == "webm"
        else signature.startswith(b"OggS")
    )
    if not valid:
        raise ValidationError("The file is not a valid video. Export it again and retry.")
    upload.content_type = VIDEO_MIME_TYPES[extension]
    return upload


def ffmpeg_executable():
    configured = getattr(settings, "CUSTOMER_VIDEO_FFMPEG", "") or shutil.which("ffmpeg")
    if configured:
        return configured
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def run_ffmpeg(arguments):
    try:
        subprocess.run(
            [ffmpeg_executable(), "-nostdin", "-hide_banner", "-loglevel", "error",
             "-y", *arguments],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            timeout=getattr(settings, "CUSTOMER_VIDEO_PROCESSING_TIMEOUT", 7200),
        )
    except subprocess.TimeoutExpired as error:
        raise ValidationError("Video processing timed out. Try a shorter video.") from error
    except subprocess.CalledProcessError as error:
        raise ValidationError(
            "This video could not be decoded. Export a playable MP4, WebM, MOV/M4V "
            "or Ogg video and try again."
        ) from error
    except (OSError, RuntimeError, ImportError) as error:
        raise ValidationError(
            "Video processing is unavailable. Please ask the administrator to check FFmpeg."
        ) from error


@contextmanager
def playback_assets(upload):
    """Keep large inputs/outputs on disk; never load a whole video into memory."""
    with TemporaryDirectory(prefix="somlab-video-") as directory:
        root = Path(directory)
        if hasattr(upload, "temporary_file_path"):
            source = Path(upload.temporary_file_path())
        else:
            source = root / ("source" + Path(upload.name).suffix.lower())
            upload.seek(0)
            with source.open("wb") as destination:
                shutil.copyfileobj(upload, destination, length=1024 * 1024)
            upload.seek(0)
        playback = root / "playback.mp4"
        poster = root / "poster.jpg"
        # Cap the longest side at 1920px without upscaling, cropping or stretching.
        # H.264/AAC and front-loaded metadata allow ranged, progressive playback.
        run_ffmpeg([
            "-protocol_whitelist", "file,pipe", "-i", str(source),
            "-map", "0:v:0", "-map", "0:a:0?", "-sn", "-dn",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-vf", "scale=w='min(1920,iw)':h='min(1920,ih)':force_original_aspect_ratio=decrease,"
                   "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-threads", "2", "-c:a", "aac", "-b:a", "96k",
            "-movflags", "+faststart", str(playback),
        ])
        run_ffmpeg([
            "-i", str(playback), "-frames:v", "1",
            "-vf", "scale=w='min(640,iw)':h='min(640,ih)':force_original_aspect_ratio=decrease",
            "-q:v", "5", str(poster),
        ])
        if not playback.stat().st_size or not poster.stat().st_size:
            raise ValidationError("Video optimization produced an empty file. Please retry.")
        yield playback, poster


def save_video_media(media, upload, *, replace_original=True):
    """Publish only after successful decoding, storage and database writes."""
    validate_video_upload(upload)
    saved_files = []
    previous_names = {
        field_name: getattr(media, field_name).name
        for field_name in ("file", "playback_file", "video_poster")
    }
    try:
        with playback_assets(upload) as (playback, poster):
            for field, path, mime in (
                (media.playback_file, playback, "video/mp4"),
                (media.video_poster, poster, "image/jpeg"),
            ):
                with path.open("rb") as source:
                    content = File(source, name=path.name)
                    content.content_type = mime
                    field.save(path.name, content, save=False)
                    saved_files.append((field.storage, field.name))
            if replace_original:
                upload.seek(0)
                media.file.save(Path(upload.name).name, upload, save=False)
                saved_files.append((media.file.storage, media.file.name))
            media.save()
    except Exception as error:
        # These are only new objects from this failed save, never existing media.
        for storage, name in saved_files:
            try:
                storage.delete(name)
            except Exception as cleanup_error:
                logger.warning("Could not clean a failed video upload (%s)", type(cleanup_error).__name__)
        for field_name, previous_name in previous_names.items():
            getattr(media, field_name).name = previous_name
        logger.warning("Video upload/optimization failed (%s)", type(error).__name__)
        raise
    return media
