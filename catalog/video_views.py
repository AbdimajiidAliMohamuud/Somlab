"""Fresh links and byte-range playback for product gallery videos."""

from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from core.customer_video import VIDEO_MIME_TYPES
from core.customer_video_views import stream_video_file
from .models import ProductMedia
from .scope import public_products


@require_safe
@never_cache
def product_video_source(request, slug, pk):
    media = get_object_or_404(
        ProductMedia.objects.filter(product__in=public_products()),
        pk=pk, media_type="video", product__slug=slug,
    )
    file = media.playback_file or media.file
    content_type = (
        "video/mp4" if media.playback_file
        else VIDEO_MIME_TYPES.get(file.name.rsplit(".", 1)[-1].lower(), "")
        if file else ""
    )
    return stream_video_file(request, file, content_type)
