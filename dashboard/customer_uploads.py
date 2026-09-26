"""Disk-backed, bounded uploads for customer video forms only."""
from pathlib import Path

from django.core.files.uploadhandler import FileUploadHandler, SkipFile, TemporaryFileUploadHandler

from core.customer_video import MAX_VIDEO_BYTES, VIDEO_LIMIT_MESSAGE, VIDEO_MIME_TYPES


class CustomerVideoLimitHandler(FileUploadHandler):
    def new_file(self, *args, **kwargs):
        super().new_file(*args, **kwargs)
        self.is_video = (
            self.field_name == "project_videos"
            or Path(self.file_name).suffix.lower().lstrip(".") in VIDEO_MIME_TYPES
        )

    def receive_data_chunk(self, raw_data, start):
        if self.is_video and start + len(raw_data) > MAX_VIDEO_BYTES:
            self.request.customer_upload_errors.append(VIDEO_LIMIT_MESSAGE)
            raise SkipFile()
        return raw_data

    def file_complete(self, file_size):
        return None


class CustomerVideoUploadMiddleware:
    upload_views = {
        "dashboard_customer_project_add", "dashboard_customer_project_edit",
        "dashboard_customer_project_media_add", "dashboard_customer_project_media_edit",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method == "POST" and request.resolver_match.url_name in self.upload_views:
            request.customer_upload_errors = []
            # Runs before CSRF parses multipart data. Large files stay on disk.
            request.upload_handlers = [
                CustomerVideoLimitHandler(request), TemporaryFileUploadHandler(request),
            ]
