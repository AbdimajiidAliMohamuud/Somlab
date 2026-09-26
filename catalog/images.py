from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat


NORMALIZED_SIZE = 1200
CONTENT_RATIO = 0.92
EDGE_TOLERANCE = 18


def _background_colour(image):
    sample_size = max(1, round(min(image.size) * 0.025))
    strips = (
        image.crop((0, 0, image.width, sample_size)),
        image.crop((0, image.height - sample_size, image.width, image.height)),
        image.crop((0, 0, sample_size, image.height)),
        image.crop((image.width - sample_size, 0, image.width, image.height)),
    )
    colours = [tuple(round(value) for value in ImageStat.Stat(strip).median[:3]) for strip in strips]
    return tuple(sorted(colour[channel] for colour in colours)[len(colours) // 2] for channel in range(3))


def _edge_connected_background_mask(image):
    """Return an alpha mask that removes only background connected to an edge.

    Colour-keying every near-white pixel would erase white instruments. Flooding
    inward from the outer edge removes the photographed canvas while retaining
    light product surfaces enclosed by their outline.
    """
    rgb = image.convert("RGB")
    background = Image.new("RGB", rgb.size, _background_colour(rgb))
    difference = ImageChops.difference(rgb, background)
    red_delta, green_delta, blue_delta = difference.split()
    maximum_channel_delta = ImageChops.lighter(
        ImageChops.lighter(red_delta, green_delta),
        blue_delta,
    ).point(
        lambda value: 255 if value <= EDGE_TOLERANCE else 0
    )

    # Flood every edge segment, rather than only the corners: a product touching
    # one edge can split an otherwise uniform backdrop into separate regions.
    flood_value = 128
    step = max(1, min(image.size) // 80)
    edge_points = (
        [(x, 0) for x in range(0, image.width, step)]
        + [(x, image.height - 1) for x in range(0, image.width, step)]
        + [(0, y) for y in range(0, image.height, step)]
        + [(image.width - 1, y) for y in range(0, image.height, step)]
    )
    for point in edge_points:
        if maximum_channel_delta.getpixel(point) == 255:
            ImageDraw.floodfill(maximum_channel_delta, point, flood_value, thresh=0)

    foreground = maximum_channel_delta.point(
        lambda value: 0 if value == flood_value else 255
    )
    # A tiny feather avoids jagged halos without cutting into the product.
    return foreground.filter(ImageFilter.GaussianBlur(radius=0.65))


def _remove_edge_background(image):
    source_alpha = image.getchannel("A")
    # Also inspect partially transparent sources: older normalized derivatives
    # may have transparent canvas corners while retaining an opaque white box.
    image.putalpha(ImageChops.multiply(source_alpha, _edge_connected_background_mask(image)))
    return image


def _content_bounds(image):
    if image.mode == "RGBA":
        alpha = image.getchannel("A")
        if alpha.getextrema()[0] < 250:
            return alpha.point(lambda value: 255 if value > 8 else 0).getbbox()

    return image.getchannel("A").point(lambda value: 255 if value > 8 else 0).getbbox()


def normalize_product_image(uploaded_file, *, filename=None):
    """Trim uniform edge space and center the complete product on a stable canvas."""
    uploaded_file.seek(0)
    with Image.open(uploaded_file) as source:
        source.load()
        image = _remove_edge_background(source.convert("RGBA"))

    bounds = _content_bounds(image)
    if bounds:
        left, top, right, bottom = bounds
        safety_margin = max(8, round(max(image.size) * 0.015))
        image = image.crop((
            max(0, left - safety_margin),
            max(0, top - safety_margin),
            min(image.width, right + safety_margin),
            min(image.height, bottom + safety_margin),
        ))

    content_size = round(NORMALIZED_SIZE * CONTENT_RATIO)
    scale = min(content_size / image.width, content_size / image.height)
    image = image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", (NORMALIZED_SIZE, NORMALIZED_SIZE), (255, 255, 255, 0))
    canvas.alpha_composite(
        image,
        ((NORMALIZED_SIZE - image.width) // 2, (NORMALIZED_SIZE - image.height) // 2),
    )

    output = BytesIO()
    canvas.save(output, format="WEBP", quality=92, method=6)
    source_name = filename or getattr(uploaded_file, "name", "product-image")
    return ContentFile(output.getvalue(), name=f"{Path(source_name).stem}.webp")
