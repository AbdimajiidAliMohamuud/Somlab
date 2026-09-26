# Somlab production deployment (Contabo)

This runbook deploys the Django application to `/var/www/somlab`, keeps its
SQLite database at `/var/lib/somlab/db.sqlite3`, runs Gunicorn under systemd,
and puts Nginx in front of it. Cloudflare R2 remains the media store and
WhiteNoise serves versioned static assets.

The commands assume Ubuntu/Debian, server IP `161.97.77.1`, and the `main`
branch of `https://github.com/AbdimajiidAliMohamuud/Somlab`.

## 1. DNS and Cloudflare

Create `A` records for `somlab.so` and `www` pointing to `161.97.77.1`. Start
with the records set to **DNS only** (grey cloud) until the origin certificate
and smoke tests work. Afterwards enable the orange cloud and set Cloudflare
SSL/TLS mode to **Full (strict)**. Do not use Flexible mode.

If staff must upload videos larger than the Cloudflare plan's request limit,
the upload cannot go through the orange-cloud proxy. Use a separate DNS-only,
access-restricted admin hostname or upload smaller files; Nginx and Django
cannot override a request rejected by Cloudflare.

## 2. First-time server setup

SSH to the server and install the runtime:

```bash
ssh root@161.97.77.1
apt update
apt install -y git python3-venv python3-dev build-essential nginx certbot python3-certbot-nginx sqlite3 ufw unattended-upgrades
mkdir -p /var/www /var/lib/somlab
```

After confirming a second SSH session can connect, enable the host firewall:

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
ufw status verbose
systemctl enable --now unattended-upgrades
```

Commit and push the release from local Git Bash. Confirm that `.env` and
`db.sqlite3` remain ignored and are not in the commit:

```bash
cd /d/Somlab
git status
git check-ignore .env db.sqlite3
git add .
git commit -m "Add production deployment configuration"
git push origin main
```

Clone that GitHub repository on the server:

```bash
git clone --branch main --single-branch \
  https://github.com/AbdimajiidAliMohamuud/Somlab.git \
  /var/www/somlab
```

If the repository is private, use a read-only GitHub deploy key. Do not put a
personal access token in the clone URL or save one in shell history.

The database and environment are deliberately transferred separately. First
make sure the local `.env` contains the production values shown in
`deploy/somlab.env.example`, especially `DJANGO_DEBUG=0`, production hosts,
SMTP, R2, and `DJANGO_DB_PATH=/var/lib/somlab/db.sqlite3`. Then, from local Git
Bash:

```bash

scp /d/Somlab/db.sqlite3 root@161.97.77.1:/tmp/somlab-db.sqlite3.upload
scp /d/Somlab/.env root@161.97.77.1:/tmp/somlab.env.upload
```

If either local file is elsewhere, change only its source path. Never put the
real `.env` in Git or in `/var/www/somlab`.

Back on the server, install and validate:

```bash
cd /var/www/somlab
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

install -o root -g www-data -m 640 /tmp/somlab.env.upload /etc/somlab.env
install -o www-data -g www-data -m 640 /tmp/somlab-db.sqlite3.upload /var/lib/somlab/db.sqlite3
rm /tmp/somlab.env.upload /tmp/somlab-db.sqlite3.upload

chown -R root:www-data /var/www/somlab
find /var/www/somlab -type d -exec chmod 750 {} \;
find /var/www/somlab -type f -exec chmod 640 {} \;
chmod 750 /var/www/somlab/venv/bin/*
chown -R www-data:www-data /var/lib/somlab
chmod 750 /var/lib/somlab

DJANGO_ENV_FILE=/etc/somlab.env ./venv/bin/python manage.py check --deploy
DJANGO_ENV_FILE=/etc/somlab.env ./venv/bin/python manage.py migrate
DJANGO_ENV_FILE=/etc/somlab.env ./venv/bin/python manage.py collectstatic --noinput
```

`check --deploy` must complete without errors. Warnings about a deliberately
short initial HSTS duration are expected; do not enable preload yet.

## 3. systemd and Nginx

On the server:

```bash
cp /var/www/somlab/deploy/somlab.service /etc/systemd/system/somlab.service
cp /var/www/somlab/deploy/nginx-somlab.conf /etc/nginx/sites-available/somlab
ln -sfn /etc/nginx/sites-available/somlab /etc/nginx/sites-enabled/somlab
rm -f /etc/nginx/sites-enabled/default

systemctl daemon-reload
systemctl enable --now somlab
systemctl status somlab --no-pager -l
nginx -t
systemctl reload nginx

curl -I -H 'Host: somlab.so' http://127.0.0.1/
```

The HTTP response may redirect to HTTPS because production redirects are on.
Issue and install the Let's Encrypt certificate after DNS resolves to this
server:

```bash
certbot --nginx -d somlab.so -d www.somlab.so --redirect
nginx -t
systemctl reload nginx
systemctl status certbot.timer --no-pager
```

Now test both names, then turn on the Cloudflare proxy:

```bash
curl -I https://somlab.so/
curl -I https://www.somlab.so/
curl -I https://somlab.so/admin/login/
```

In Cloudflare, set SSL/TLS to **Full (strict)** and enable **Always Use HTTPS**.
Avoid duplicate Cloudflare redirect rules that bounce `www` and the apex back
and forth.

## 4. Normal code update

Commit and push the new release to `main` from the local computer. Then run on
the server (the live database and environment are outside the repository):

```bash
cd /var/www/somlab
git status --short
git pull --ff-only origin main
./venv/bin/pip install -r requirements.txt
DJANGO_ENV_FILE=/etc/somlab.env ./venv/bin/python manage.py check --deploy
DJANGO_ENV_FILE=/etc/somlab.env ./venv/bin/python manage.py migrate
DJANGO_ENV_FILE=/etc/somlab.env ./venv/bin/python manage.py collectstatic --noinput
systemctl restart somlab
systemctl status somlab --no-pager -l
journalctl -u somlab -n 100 --no-pager
```

## 5. Replacing the production SQLite database

Do not overwrite a live SQLite file. Upload to a temporary filename, verify it,
stop the service, retain a rollback copy, and then install it:

```bash
# Local Git Bash
scp /d/Somlab/db.sqlite3 root@161.97.77.1:/tmp/somlab-db.sqlite3.upload
```

```bash
# Server
sqlite3 /tmp/somlab-db.sqlite3.upload 'PRAGMA integrity_check;'
systemctl stop somlab
sqlite3 /var/lib/somlab/db.sqlite3 ".backup '/var/lib/somlab/db.sqlite3.before-upload'"
install -o www-data -g www-data -m 640 /tmp/somlab-db.sqlite3.upload /var/lib/somlab/db.sqlite3
rm /tmp/somlab-db.sqlite3.upload
cd /var/www/somlab
DJANGO_ENV_FILE=/etc/somlab.env ./venv/bin/python manage.py migrate
systemctl start somlab
systemctl status somlab --no-pager -l
```

Only use that procedure when intentionally replacing production data. For
ordinary deployments, run migrations against the existing production DB.

## 6. Backups and operations

Back up SQLite with its online backup command, not `cp` while the site is
running:

```bash
mkdir -p /var/backups/somlab
sqlite3 /var/lib/somlab/db.sqlite3 ".backup '/var/backups/somlab/db-$(date +%F-%H%M%S).sqlite3'"
```

Copy encrypted backups off the Contabo server and test a restore periodically.
Enable Cloudflare R2 object versioning/lifecycle protection if available, and
keep R2 credentials bucket-scoped. Database backups do not contain R2 objects.

Useful checks:

```bash
systemctl status somlab nginx --no-pager -l
journalctl -u somlab -f
tail -f /var/log/nginx/access.log /var/log/nginx/error.log
certbot renew --dry-run
df -h
free -h
```

Also mirror ports 22, 80, and 443 in the Contabo firewall, use SSH keys, disable
password/root SSH after confirming a sudo account works, and configure
uptime/error monitoring. SQLite is acceptable for a modest, mostly-read site;
move to PostgreSQL if write traffic or multiple app servers grow.
