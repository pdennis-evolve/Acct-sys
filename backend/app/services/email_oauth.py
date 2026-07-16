"""Per-tenant-user OAuth against Microsoft Graph and Gmail, so invoices
send *as* the sending user rather than a shared SMTP relay (brief Phase
9). This sandbox has no real Azure AD app registration or Google Cloud
OAuth client -- MICROSOFT_CLIENT_ID/SECRET and GOOGLE_CLIENT_ID/SECRET
are unset. Every function here checks is_configured() first and raises
IntegrationNotConfigured rather than fabricating an authorize URL, a
token, or a sent email. The HTTP calls below are real Graph/Gmail API
calls and are the code path any real deployment runs through once
credentials are supplied -- they are simply never exercised in this
environment for lack of credentials.
"""
import secrets
from datetime import datetime, timedelta, timezone

import requests
from flask import current_app

MICROSOFT_SCOPES = "offline_access Mail.Send User.Read"
GOOGLE_SCOPES = "https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/userinfo.email"


class IntegrationNotConfigured(Exception):
    pass


def is_configured(provider: str) -> bool:
    if provider == "microsoft":
        return bool(current_app.config.get("MICROSOFT_CLIENT_ID") and current_app.config.get("MICROSOFT_CLIENT_SECRET"))
    if provider == "google":
        return bool(current_app.config.get("GOOGLE_CLIENT_ID") and current_app.config.get("GOOGLE_CLIENT_SECRET"))
    return False


def _redirect_uri(provider: str) -> str:
    return f"{current_app.config['API_BASE_URL']}/api/settings/integrations/{provider}/callback"


def build_authorize_url(provider: str, state: str) -> str:
    if not is_configured(provider):
        raise IntegrationNotConfigured(f"{provider} is not configured for this environment")

    redirect_uri = _redirect_uri(provider)
    if provider == "microsoft":
        tenant = current_app.config["MICROSOFT_TENANT"]
        params = {
            "client_id": current_app.config["MICROSOFT_CLIENT_ID"],
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": MICROSOFT_SCOPES,
            "state": state,
        }
        return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{_urlencode(params)}"

    if provider == "google":
        params = {
            "client_id": current_app.config["GOOGLE_CLIENT_ID"],
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": GOOGLE_SCOPES,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{_urlencode(params)}"

    raise ValueError(f"Unknown provider: {provider}")


def _urlencode(params: dict) -> str:
    from urllib.parse import urlencode
    return urlencode(params)


def generate_state() -> str:
    return secrets.token_urlsafe(24)


def exchange_code(provider: str, code: str) -> dict:
    """Returns {access_token, refresh_token, expires_at, email_address}."""
    if not is_configured(provider):
        raise IntegrationNotConfigured(f"{provider} is not configured for this environment")

    redirect_uri = _redirect_uri(provider)

    if provider == "microsoft":
        tenant = current_app.config["MICROSOFT_TENANT"]
        resp = requests.post(
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            data={
                "client_id": current_app.config["MICROSOFT_CLIENT_ID"],
                "client_secret": current_app.config["MICROSOFT_CLIENT_SECRET"],
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "scope": MICROSOFT_SCOPES,
            },
            timeout=15,
        )
        resp.raise_for_status()
        token_data = resp.json()

        me = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
            timeout=15,
        )
        me.raise_for_status()
        email_address = me.json().get("mail") or me.json().get("userPrincipalName")

        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600)),
            "email_address": email_address,
        }

    if provider == "google":
        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": current_app.config["GOOGLE_CLIENT_ID"],
                "client_secret": current_app.config["GOOGLE_CLIENT_SECRET"],
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            timeout=15,
        )
        resp.raise_for_status()
        token_data = resp.json()

        me = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
            timeout=15,
        )
        me.raise_for_status()
        email_address = me.json().get("email")

        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600)),
            "email_address": email_address,
        }

    raise ValueError(f"Unknown provider: {provider}")


def refresh_access_token(connection) -> dict:
    provider = connection.provider
    if not is_configured(provider):
        raise IntegrationNotConfigured(f"{provider} is not configured for this environment")
    if not connection.refresh_token:
        raise IntegrationNotConfigured("No refresh token on file; the user must reconnect")

    if provider == "microsoft":
        tenant = current_app.config["MICROSOFT_TENANT"]
        resp = requests.post(
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            data={
                "client_id": current_app.config["MICROSOFT_CLIENT_ID"],
                "client_secret": current_app.config["MICROSOFT_CLIENT_SECRET"],
                "grant_type": "refresh_token",
                "refresh_token": connection.refresh_token,
                "scope": MICROSOFT_SCOPES,
            },
            timeout=15,
        )
        resp.raise_for_status()
        token_data = resp.json()
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", connection.refresh_token),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600)),
        }

    if provider == "google":
        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": current_app.config["GOOGLE_CLIENT_ID"],
                "client_secret": current_app.config["GOOGLE_CLIENT_SECRET"],
                "grant_type": "refresh_token",
                "refresh_token": connection.refresh_token,
            },
            timeout=15,
        )
        resp.raise_for_status()
        token_data = resp.json()
        return {
            "access_token": token_data["access_token"],
            "refresh_token": connection.refresh_token,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600)),
        }

    raise ValueError(f"Unknown provider: {provider}")


def ensure_fresh_token(connection) -> str:
    """Refreshes and persists the connection's token if it's expired.
    Returns a valid access_token. Caller must db.session.commit()."""
    if connection.token_expires_at > datetime.now(timezone.utc) + timedelta(minutes=2):
        return connection.access_token

    refreshed = refresh_access_token(connection)
    connection.access_token = refreshed["access_token"]
    connection.refresh_token = refreshed["refresh_token"]
    connection.token_expires_at = refreshed["expires_at"]
    return connection.access_token


def send_mail(connection, to_email: str, subject: str, html_body: str, attachment_bytes: bytes | None = None,
              attachment_filename: str | None = None, attachment_content_type: str = "application/pdf") -> None:
    if not is_configured(connection.provider):
        raise IntegrationNotConfigured(f"{connection.provider} is not configured for this environment")

    access_token = ensure_fresh_token(connection)

    if connection.provider == "microsoft":
        message = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": html_body},
                "toRecipients": [{"emailAddress": {"address": to_email}}],
            },
            "saveToSentItems": True,
        }
        if attachment_bytes:
            import base64
            message["message"]["attachments"] = [{
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": attachment_filename or "attachment.pdf",
                "contentType": attachment_content_type,
                "contentBytes": base64.b64encode(attachment_bytes).decode("ascii"),
            }]
        resp = requests.post(
            "https://graph.microsoft.com/v1.0/me/sendMail",
            headers={"Authorization": f"Bearer {access_token}"},
            json=message,
            timeout=20,
        )
        resp.raise_for_status()
        return

    if connection.provider == "google":
        import base64
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.application import MIMEApplication

        msg = MIMEMultipart()
        msg["To"] = to_email
        msg["From"] = connection.email_address
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))
        if attachment_bytes:
            part = MIMEApplication(attachment_bytes, Name=attachment_filename or "attachment.pdf")
            part["Content-Disposition"] = f'attachment; filename="{attachment_filename or "attachment.pdf"}"'
            msg.attach(part)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
        resp = requests.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"raw": raw},
            timeout=20,
        )
        resp.raise_for_status()
        return

    raise ValueError(f"Unknown provider: {connection.provider}")
