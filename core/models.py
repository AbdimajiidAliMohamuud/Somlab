from urllib.parse import parse_qs, urlparse

from django.db import models
from django.urls import reverse

from catalog.labels import catalogue_display_label


class Service(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    short_description = models.CharField(max_length=220)
    description = models.TextField()
    icon = models.CharField(max_length=32, default="tools")
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("display_order", "name")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("service_detail", args=[self.slug])


class Partner(models.Model):
    EQUIPMENT_GROUPS = [
        ("laboratory", "Laboratory"),
        ("medical", "Medical Equipment"),
        ("dental", "Dental Equipment"),
    ]

    name = models.CharField(max_length=120)
    country = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="partners/", blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    equipment_group = models.CharField(
        max_length=20,
        choices=EQUIPMENT_GROUPS,
        blank=True,
        help_text="Show this manufacturer in the Products & Solutions menu.",
    )
    menu_label = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional shorter manufacturer name for the menu.",
    )
    menu_order = models.PositiveSmallIntegerField(default=0, blank=True)
    menu_categories = models.ManyToManyField(
        "catalog.Category",
        blank=True,
        related_name="menu_manufacturers",
        help_text="Categories displayed beneath this manufacturer.",
    )

    class Meta:
        ordering = ("display_order", "name")

    def __str__(self):
        return self.name

    @property
    def navigation_name(self):
        return catalogue_display_label(
            self.name,
            self.menu_label or self.name,
        )


class Testimonial(models.Model):
    RATING_CHOICES = [(value, str(value)) for value in range(1, 6)]

    customer_name = models.CharField(max_length=120)
    organization = models.CharField(max_length=160)
    review = models.TextField()
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        null=True,
        blank=True,
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("display_order", "id")

    def __str__(self):
        return f"{self.customer_name} — {self.organization}"

    @property
    def rating_stars(self):
        return "★" * (self.rating or 0)


class Customer(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to="customers/logos/", blank=True)
    website = models.URLField(blank=True)
    short_description = models.TextField(blank=True)
    description = models.TextField(blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    other_url = models.URLField(blank=True)
    products = models.ManyToManyField(
        "catalog.Product",
        blank=True,
        related_name="customers",
    )
    display_order = models.PositiveSmallIntegerField(default=0, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("display_order", "name")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("customer_detail", args=[self.slug])


class CustomerProject(models.Model):
    WORK_TYPES = [
        ("supply", "Products supplied"),
        ("installation", "Equipment installed"),
        ("project", "Project completed"),
        ("service", "Service delivered"),
        ("other", "Other completed work"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    title = models.CharField(max_length=180)
    work_type = models.CharField(
        max_length=20,
        choices=WORK_TYPES,
        default="project",
    )
    description = models.TextField(blank=True)
    date = models.DateField(null=True, blank=True)
    products = models.ManyToManyField(
        "catalog.Product",
        blank=True,
        related_name="customer_projects",
        help_text="Existing Somlab products supplied or installed in this project.",
    )
    display_order = models.PositiveSmallIntegerField(default=0, blank=True)

    class Meta:
        ordering = ("display_order", "-date", "id")

    def __str__(self):
        return f"{self.customer}: {self.title}"


class CustomerProjectMedia(models.Model):
    VIDEO_MIME_TYPES = {
        "mp4": "video/mp4",
        "m4v": "video/mp4",
        "mov": "video/quicktime",
        "webm": "video/webm",
        "ogv": "video/ogg",
        "ogg": "video/ogg",
    }
    MEDIA_TYPES = [
        ("image", "Image"),
        ("video", "Video"),
    ]

    project = models.ForeignKey(
        CustomerProject,
        on_delete=models.CASCADE,
        related_name="media",
    )
    file = models.FileField(upload_to="customers/projects/", blank=True)
    playback_file = models.FileField(upload_to="customers/projects/playback/", blank=True)
    video_poster = models.ImageField(upload_to="customers/projects/posters/", blank=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    video_url = models.URLField(
        blank=True,
        help_text="Optional YouTube, Vimeo, or other external video URL.",
    )
    caption = models.CharField(max_length=240, blank=True)
    description = models.TextField(blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("display_order", "id")
        verbose_name_plural = "customer project media"

    def __str__(self):
        source = self.file.name.rsplit("/", 1)[-1] if self.file else self.video_url
        return f"{self.project}: {self.get_media_type_display()} — {source}"

    @property
    def embed_url(self):
        """Return a privacy-conscious embed URL for supported providers."""
        if not self.video_url:
            return ""
        parsed = urlparse(self.video_url)
        host = parsed.netloc.casefold().removeprefix("www.")
        path_parts = [part for part in parsed.path.split("/") if part]

        video_id = ""
        if host == "youtu.be" and path_parts:
            video_id = path_parts[0]
        elif host in {"youtube.com", "m.youtube.com"}:
            if parsed.path == "/watch":
                video_id = parse_qs(parsed.query).get("v", [""])[0]
            elif len(path_parts) >= 2 and path_parts[0] in {"embed", "shorts"}:
                video_id = path_parts[1]
        if video_id:
            return f"https://www.youtube-nocookie.com/embed/{video_id}"

        if host in {"vimeo.com", "player.vimeo.com"} and path_parts:
            video_id = path_parts[-1]
            if video_id.isdigit():
                return f"https://player.vimeo.com/video/{video_id}"
        return ""

    @property
    def video_mime_type(self):
        if not self.file:
            return ""
        extension = self.file.name.rsplit(".", 1)[-1].casefold()
        return self.VIDEO_MIME_TYPES.get(extension, "")


class AboutPageContent(models.Model):
    hero_eyebrow = models.CharField(max_length=80, default="About Somlab")
    hero_title = models.CharField(max_length=220, default="Built around reliable laboratory performance.")
    hero_intro = models.TextField(default="Serving hospitals, private laboratories, universities, research organisations and clinics across East Africa.")
    story_eyebrow = models.CharField(max_length=80, default="Who we are")
    story_title = models.CharField(max_length=220, default="A laboratory solutions company with a long-term view.")
    story_paragraph_one = models.TextField(default="Founded in 2022 as a sister company of Medisom Health Group, Somlab Diagnostics imports, distributes and installs quality laboratory equipment, reagents and supplies.")
    story_paragraph_two = models.TextField(default="We support customers beyond delivery through training, maintenance, laboratory management systems and customised turnkey projects.")
    vision_title = models.CharField(max_length=80, default="Our vision")
    vision_body = models.TextField(default="To become a leading laboratory solutions provider in East Africa by delivering reliable products, excellent service and long-term value.")
    mission_title = models.CharField(max_length=80, default="Our mission")
    mission_body = models.TextField(default="To build lasting partnerships by providing quality laboratory products, innovative solutions and dependable technical support.")
    promise_title = models.CharField(max_length=80, default="Our promise")
    promise_body = models.TextField(default="We deliver what we promise and promise only what we can deliver—with integrity, care and consistent performance.")
    values_eyebrow = models.CharField(max_length=80, default="Our values")
    values_title = models.CharField(max_length=150, default="How we work")
    integrity_title = models.CharField(max_length=80, default="Integrity")
    integrity_body = models.TextField(default="Honesty, fairness and transparency in every relationship.")
    reliability_title = models.CharField(max_length=80, default="Reliability")
    reliability_body = models.TextField(default="Dependable products, communication and follow-through.")
    teamwork_title = models.CharField(max_length=80, default="Teamwork")
    teamwork_body = models.TextField(default="Working closely with customers, suppliers and technical teams.")
    customer_focus_title = models.CharField(max_length=80, default="Customer focus")
    customer_focus_body = models.TextField(default="Solutions shaped around the realities of each institution.")
    service_excellence_title = models.CharField(max_length=80, default="Service excellence")
    service_excellence_body = models.TextField(default="Responsive support delivered efficiently and professionally.")
    audience_eyebrow = models.CharField(max_length=80, default="Who we serve")
    audience_title = models.CharField(max_length=180, default="Supporting health and science across the region")
    audiences = models.TextField(
        default="Hospitals\nPrivate laboratories\nClinics\nBlood banks\nUniversities\nResearch centres\nGovernment institutions\nHumanitarian organisations",
        help_text="One audience per line.",
    )

    @property
    def audience_items(self):
        return [item.strip() for item in self.audiences.splitlines() if item.strip()]

    def __str__(self):
        return "About Us content"


class ContactPageContent(models.Model):
    hero_eyebrow = models.CharField(max_length=80, default="Contact us")
    hero_title = models.CharField(max_length=220, default="Let’s solve your laboratory requirement.")
    hero_intro = models.TextField(default="Ask about products, availability, technical services or your current order.")
    details_eyebrow = models.CharField(max_length=80, default="Somlab Diagnostics")
    details_title = models.CharField(max_length=150, default="Talk to our team")
    details_intro = models.TextField(default="We usually respond during business hours. For urgent product enquiries, call or WhatsApp our sales team.")
    email = models.EmailField(default="info@somlab.so")
    primary_phone = models.CharField(max_length=40, default="+252 616 119117")
    secondary_phone = models.CharField(max_length=40, default="+90 534 820 0301", blank=True)
    office_address = models.TextField(default="Star Home Tower, 5th Floor, Apt. 504\nKM5, Amira Hotel Street, Hodan District\nMogadishu, Somalia")
    form_title = models.CharField(max_length=120, default="Send a message")

    @staticmethod
    def _tel(phone):
        return "".join(char for char in phone if char.isdigit() or char == "+")

    @property
    def primary_phone_tel(self):
        return self._tel(self.primary_phone)

    @property
    def secondary_phone_tel(self):
        return self._tel(self.secondary_phone)

    def __str__(self):
        return "Contact Us content"


class ContactMessage(models.Model):
    full_name = models.CharField(max_length=120)
    company_name = models.CharField(max_length=160, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=40)
    subject = models.CharField(max_length=180)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.full_name}: {self.subject}"
