# Somlab Diagnostics

A focused Django website for Somlab Diagnostics: corporate pages, a laboratory
product catalogue, customer accounts and a staff inquiry-management dashboard.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_somlab
python manage.py createsuperuser
python manage.py runserver
```

Open:

- Website: `http://127.0.0.1:8000/`
- Staff dashboard: `http://127.0.0.1:8000/dashboard/`

Only active users explicitly marked as **Staff status** can access the operations
dashboard. Customer accounts receive a `403 Forbidden` response if they attempt
to open any dashboard screen.
Products, categories, partners, services, inquiries and messages are managed
inside this custom dashboard. The Django built-in admin is not exposed.
Authorized administrators can add other dashboard users from **Dashboard →
Users**.

## Cloudflare R2 media storage

Uploaded product, category and partner images can be stored in the `somlab`
Cloudflare R2 bucket. Static CSS and JavaScript remain served by WhiteNoise.

1. Revoke any R2 credential that has been pasted into chat, source code or logs.
2. Create a new bucket-scoped **Object Read & Write** S3 credential.
3. Copy `.env.example` to `.env` locally, or configure the same keys using your
   hosting platform's encrypted environment/secrets settings.
4. Set `R2_ENABLED=1`.
5. Set `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY` from the replacement
   credential. Never commit these values.
6. Leave `R2_PUBLIC_URL` empty to serve images through one-hour signed URLs.
   Once a public custom domain is connected and verified, set it to a domain
   such as `https://media.somlab.so`.

The application uploads files under the `media/` prefix. When `R2_PUBLIC_URL`
is empty, Django generates signed S3 URLs. When it is set, Django generates
unsigned public URLs from that domain. CORS is not needed for the current
server-side upload forms. Add a restricted CORS policy only if direct browser
uploads are introduced later.

To copy existing files from the local `media/` directory into R2 without
changing their database paths:

```bash
python manage.py migrate_media_to_storage
```

The command skips objects that already exist. Pass `--overwrite` to replace
matching R2 objects. Local files are retained as a backup.

### Safe R2 cleanup

Run the cleanup audit in the production environment so it scans the current
production database and configuration. Dry-run is the default and cannot
delete objects:

```bash
python manage.py cleanup_r2
```

The command scans every database file/image field, textual and JSON content,
settings, templates, CSS, JavaScript and application source. It writes a
timestamped manifest under `r2_cleanup_reports/`, lists every unused key and
reports recoverable space. Objects outside the configured `media/` storage
prefix are protected.

Review that manifest before deletion. Deletion requires the same manifest and
the exact confirmation token:

```bash
python manage.py cleanup_r2 \
  --verify \
  --manifest r2_cleanup_reports/dry-run-YYYYMMDDTHHMMSSZ.json
```

Verification rescans all references and rechecks every candidate's current R2
size, ETag and last-modified time without deleting anything. It produces a
verified-only manifest. Use that verified manifest for the deletion command:

```bash
python manage.py cleanup_r2 \
  --delete \
  --manifest r2_cleanup_reports/dry-run-YYYYMMDDTHHMMSSZ.verified.json \
  --confirm DELETE-UNUSED-R2
```

Before each deletion, the command rescans all references and verifies that the
object's size and ETag still match the reviewed manifest. Newly referenced,
changed or missing objects are skipped. Every successful deletion is recorded
in a JSON Lines audit log beside the manifest. Running `--delete` without both
the reviewed manifest and confirmation token is refused.

For customer project uploads only, use `python manage.py cleanup_customer_media_r2`
to list orphan objects without deleting them. It checks references across the
site and protects objects uploaded in the last 24 hours. After reviewing the
output, `python manage.py cleanup_customer_media_r2 --delete` rechecks each
candidate's references, size, ETag, and age before removal. It never scans or
deletes static assets or media outside `media/customers/projects/`.

## Product inquiry workflow

A submitted product inquiry is saved in **Admin → Product inquiries** and a
notification is sent to `info@somlab.so`. Failed delivery is logged without
discarding the saved inquiry. About Us and Contact Us page text can be edited
under **Admin → Website**. Historical orders remain in the database but are no
longer exposed in the custom dashboard.

## Production notes

Run `python manage.py migrate` against the production database before serving a
new release. In particular, `core.0014_aboutpagecontent_contactpagecontent`
creates the About Us and Contact Us admin content tables; deploying the code
without applying it makes `/admin/about/` and `/admin/contact/` fail.

Configure `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`,
`DJANGO_EMAIL_HOST_USER`, `DJANGO_EMAIL_HOST_PASSWORD` and
`DJANGO_DEFAULT_FROM_EMAIL` for a trusted SMTP provider. Production requires
the SMTP backend and exactly one of `DJANGO_EMAIL_USE_TLS=1` (typically port
587) or `DJANGO_EMAIL_USE_SSL=1` (typically port 465). Keep credentials in the
deployment environment, not source control. The console backend remains
available in development.

Customer videos accept MP4, WebM, MOV/M4V and Ogg files up to 999,999,999 bytes
each (strictly under 1 decimal GB). Install `requirements.txt` for the bundled
FFmpeg runtime, or set `CUSTOMER_VIDEO_FFMPEG` to a maintained system FFmpeg.
The admin keeps original uploads and creates H.264/AAC MP4 playback copies with
fast-start metadata and poster images in the same media/R2 storage. Existing
videos can be prepared once with `python manage.py prepare_customer_videos ID`.

Large uploads are streamed to temporary disk. Provision disk for the originals
and playback copies, and set the origin server's request-body limit to at least
6 GB for the six-file form (for example, Nginx `client_max_body_size 6G`). Allow
enough request/worker time for upload plus conversion (the processing timeout
defaults to 7200 seconds via `CUSTOMER_VIDEO_PROCESSING_TIMEOUT`). If a CDN or
proxy has a smaller upload limit, use an authenticated admin origin with that
limit raised; Django cannot override a request rejected upstream. These settings
must be applied to the customer admin upload routes on the deployment host.

Set `DJANGO_DEBUG=0`, provide a strong unique `DJANGO_SECRET_KEY`, and list only
the production hostnames in `DJANGO_ALLOWED_HOSTS`. Set
`DJANGO_CSRF_TRUSTED_ORIGINS` to the corresponding HTTPS origins (the application
derives them from allowed hosts when omitted). Enable `DJANGO_TRUST_PROXY_PROTO=1`
only when a trusted reverse proxy strips and sets `X-Forwarded-Proto`.

HTTPS redirect, secure cookies, security headers and a staged one-hour HSTS policy
are enabled automatically when debug mode is off. Increase HSTS deliberately
after confirming HTTPS across the deployment; enable subdomains/preload only when
every affected host is HTTPS. Configure a real email backend and serve uploaded
media from persistent object storage such as the existing R2 integration. SQLite
is appropriate for local evaluation; use PostgreSQL for production.
