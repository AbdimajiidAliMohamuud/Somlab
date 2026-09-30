"""Product inquiry SMTP credentials and delivery configuration."""

import base64
import hashlib
import re
import smtplib
import socket

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import get_connection


def _cipher():
    # A stable, private production SECRET_KEY is required to decrypt stored passwords.
    key_material = f"somlab-inquiry-smtp-v1:{settings.SECRET_KEY}".encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(key_material).digest())
    return Fernet(key)


def encrypt_app_password(password):
    return _cipher().encrypt(password.encode()).decode()


def decrypt_app_password(ciphertext):
    if not ciphertext:
        raise ImproperlyConfigured("The inquiry SMTP App Password is not configured.")
    try:
        return _cipher().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, ValueError) as error:
        raise ImproperlyConfigured(
            "The inquiry SMTP App Password cannot be decrypted; check the server secret key."
        ) from error


def inquiry_connection(email_settings, *, backend=None):
    return get_connection(
        backend=backend,
        host=email_settings.smtp_host,
        port=email_settings.smtp_port,
        username=email_settings.smtp_username,
        password=decrypt_app_password(email_settings.app_password_encrypted),
        use_tls=email_settings.use_tls,
        use_ssl=False,
        timeout=settings.EMAIL_TIMEOUT,
    )


def format_smtp_failure(error, email_settings):
    """Return an actionable SMTP reason without echoing credentials."""
    if isinstance(error, smtplib.SMTPResponseException):
        reply = error.smtp_error
        if isinstance(reply, bytes):
            reply = reply.decode("utf-8", errors="replace")
        reason = f"SMTP {error.smtp_code}: {reply}"
    elif isinstance(error, smtplib.SMTPRecipientsRefused):
        reason = "The SMTP server refused the recipient address."
    elif isinstance(error, smtplib.SMTPServerDisconnected):
        reason = "The SMTP server disconnected during delivery."
    elif isinstance(error, (socket.timeout, TimeoutError)):
        reason = "The connection to the SMTP server timed out."
    elif isinstance(error, socket.gaierror):
        reason = "The SMTP host could not be resolved."
    elif isinstance(error, ConnectionRefusedError):
        reason = "The SMTP server refused the connection."
    elif isinstance(error, ImproperlyConfigured):
        reason = str(error)
    elif isinstance(error, OSError):
        reason = f"SMTP connection error: {error.strerror or type(error).__name__}"
    elif isinstance(error, RuntimeError) and str(error) == "No email was delivered":
        reason = "The SMTP server accepted no message."
    else:
        reason = f"Unexpected delivery error ({type(error).__name__})."

    try:
        password = decrypt_app_password(email_settings.app_password_encrypted)
    except ImproperlyConfigured:
        password = ""
    secrets = (
        email_settings.smtp_username,
        email_settings.app_password_encrypted,
        password,
        "".join(password.split()),
    )
    for secret in secrets:
        if secret:
            reason = re.sub(re.escape(secret), "[redacted]", reason, flags=re.IGNORECASE)
    return " ".join(reason.split())[:240]
