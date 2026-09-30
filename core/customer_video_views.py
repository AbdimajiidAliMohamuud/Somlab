"""Fresh R2 playback links, and byte-range playback for local development."""
import re

from django.http import HttpResponse, HttpResponseRedirect, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from .models import CustomerProjectMedia


@require_safe
@never_cache
def customer_video_source(request, slug, pk):
    media = get_object_or_404(
        CustomerProjectMedia.objects.select_related("project__customer"),
        pk=pk, media_type="video", project__customer__slug=slug,
        project__customer__is_active=True,
    )
    file = media.playback_file or media.file
    return stream_video_file(
        request, file,
        "video/mp4" if media.playback_file else media.video_mime_type,
    )


def stream_video_file(request, file, content_type):
    """Redirect R2 playback or stream local byte ranges without buffering a video."""
    if not file:
        return HttpResponse(status=404)
    url = file.url
    if url.startswith(("https://", "http://")):
        # A fresh redirect avoids embedding expiring R2 signatures in cached pages.
        return HttpResponseRedirect(url)

    size = file.size
    start, end, status = 0, size - 1, 200
    range_header = request.headers.get("Range")
    if range_header:
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header)
        if not match or not any(match.groups()):
            return HttpResponse(status=416, headers={"Content-Range": f"bytes */{size}"})
        first, last = match.groups()
        start = int(first) if first else max(0, size - int(last))
        end = min(int(last), size - 1) if first and last else size - 1
        if start > end or start >= size:
            return HttpResponse(status=416, headers={"Content-Range": f"bytes */{size}"})
        status = 206

    def chunks():
        with file.open("rb") as source:
            source.seek(start)
            remaining = end - start + 1
            while remaining:
                chunk = source.read(min(65536, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    response = StreamingHttpResponse(
        () if request.method == "HEAD" else chunks(), status=status,
        content_type=content_type or "application/octet-stream",
    )
    response["Accept-Ranges"] = "bytes"
    response["Content-Length"] = end - start + 1
    response["Content-Disposition"] = "inline"
    if status == 206:
        response["Content-Range"] = f"bytes {start}-{end}/{size}"
    return response
