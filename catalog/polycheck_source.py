import html
import json
import os
import ssl
from html.parser import HTMLParser
from urllib.request import Request, urlopen


POLYCHECK_INDEX_URL = "https://polycheck.de/alternative-products/"
TABLE_GROUPS = {
    "table_id_3023": "Autoimmune",
    "table_id_3024": "Allergy",
    "table_id_3025": "Veterinary",
}


def polycheck_ssl_context():
    configured = os.environ.get("SSL_CERT_FILE")
    if configured:
        return ssl.create_default_context(cafile=configured)
    system_bundle = "/etc/ssl/cert.pem"
    if os.path.isfile(system_bundle):
        return ssl.create_default_context(cafile=system_bundle)
    return ssl.create_default_context()


class PolycheckCatalogueParser(HTMLParser):
    """Extract the official WooCommerce catalogue without external parsers."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.products = []
        self.seen_urls = set()
        self.group = None
        self.table_depth = 0
        self.product = None
        self.product_row_depth = 0
        self.description_depth = 0
        self.component_row = None
        self.component_cell = None

    @staticmethod
    def _attrs(attributes):
        return dict(attributes)

    def handle_starttag(self, tag, attributes):
        attrs = self._attrs(attributes)
        if self.group:
            if tag == "div":
                self.table_depth += 1
        elif tag == "div" and attrs.get("id") in TABLE_GROUPS:
            self.group = TABLE_GROUPS[attrs["id"]]
            self.table_depth = 1

        if self.group and tag == "tr" and attrs.get("data-href") and not self.product:
            url = attrs["data-href"]
            if url in self.seen_urls:
                return
            variations = []
            try:
                variations = json.loads(html.unescape(attrs.get("data-product_variations", "[]")))
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
            self.product = {
                "group": self.group,
                "name": attrs.get("data-title", "").strip(),
                "source_url": url,
                "source_id": attrs.get("data-product_id", "").strip(),
                "row_sku": attrs.get("data-sku", "").strip(),
                "components": [],
                "variants": self._variants(variations),
                "image_url": self._variation_image(variations),
            }
            self.product_row_depth = 1
            return

        if not self.product:
            return
        if tag == "tr":
            self.product_row_depth += 1
        if tag == "div" and "wpt_short_description" in attrs.get("class", "").split():
            self.description_depth = 1
        elif self.description_depth and tag == "div":
            self.description_depth += 1
        if self.description_depth and tag == "tr":
            self.component_row = []
        elif self.description_depth and tag == "td":
            self.component_cell = []
        if tag == "img" and not self.product["image_url"]:
            self.product["image_url"] = attrs.get("data-src") or attrs.get("src") or ""

    def handle_data(self, data):
        if self.component_cell is not None:
            self.component_cell.append(data)

    def handle_endtag(self, tag):
        if self.product:
            if tag == "td" and self.component_cell is not None:
                value = " ".join("".join(self.component_cell).split())
                if value and self.component_row is not None:
                    self.component_row.append(value)
                self.component_cell = None
            elif tag == "tr" and self.component_row is not None:
                value = " ".join(self.component_row).strip()
                if value and value != "|":
                    self.product["components"].append(value)
                self.component_row = None
            if tag == "div" and self.description_depth:
                self.description_depth -= 1
            if tag == "tr":
                self.product_row_depth -= 1
                if self.product_row_depth == 0:
                    self._finish_product()

        if self.group and tag == "div":
            self.table_depth -= 1
            if self.table_depth == 0:
                self.group = None

    def _finish_product(self):
        if self.product["name"] and self.product["source_url"]:
            self.seen_urls.add(self.product["source_url"])
            self.products.append(self.product)
        self.product = None
        self.description_depth = 0
        self.component_row = None
        self.component_cell = None

    @staticmethod
    def _variants(variations):
        variants = []
        seen = set()
        for variation in variations:
            attributes = variation.get("attributes") or {}
            label = next((str(value) for value in attributes.values() if value), "")
            sku = str(variation.get("sku") or "").strip()
            key = (label, sku)
            if key in seen or not any(key):
                continue
            seen.add(key)
            variants.append({"name": label, "sku": sku})
        return variants

    @staticmethod
    def _variation_image(variations):
        for variation in variations:
            image = variation.get("image") or {}
            for key in ("full_src", "url", "src"):
                if image.get(key):
                    return image[key]
        return ""


def parse_polycheck_catalogue(source_html):
    parser = PolycheckCatalogueParser()
    parser.feed(source_html)
    return parser.products


def fetch_polycheck_catalogue(timeout=45):
    request = Request(
        POLYCHECK_INDEX_URL,
        headers={"User-Agent": "Somlab catalogue importer/1.0"},
    )
    with urlopen(request, timeout=timeout, context=polycheck_ssl_context()) as response:
        source_html = response.read().decode(response.headers.get_content_charset() or "utf-8")
    return parse_polycheck_catalogue(source_html)
